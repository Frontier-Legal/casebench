// The Settings page in the browser (decision 0063); the API is tested in
// tests/workbench/test_settings.py.

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { Me, SettingsView } from "@/lib/api"

const ENGINEER: Me = { name: "Deniz", view: "engineering", role_locked: false, role: "engineer", setup: true }
const SECRET = "sk-test-0123456789"

const VIEW: SettingsView = {
  file: "casebench.yaml",
  exists: true,
  editable: true,
  problem: null,
  has_comments: false,
  sections: {
    target: { type: "python", entry: "agent.py:answer" },
    judges: [{ provider: "anthropic", model: "claude-judge", price: { input: 3, output: 15 } }],
    workbench: { try_daily_limit_usd: 5 },
  },
  text: "target:\n  type: python\n",
  models: [
    {
      role: "judge",
      used_for: "Lists each answer's citations, matches them to the corpus and checks what they claim; grades criteria",
      provider: "anthropic",
      model: "claude-judge",
      family: "claude",
      max_tokens: 4096,
      context_window: 200000,
      price_input: 3,
      price_output: 15,
      settings: { reasoning_effort: "low" },
      key: "ANTHROPIC_API_KEY",
      base_url: null,
    },
  ],
  keys: [{ name: "ANTHROPIC_API_KEY", where: "missing", file: null, used_by: ["judge"] }],
  budget: { target: "answer", limit: 5, spent_today: 1.25, remaining: 3.75, can_ask: true, why_not: null, checks_citations: true },
  runs: [{ run_id: "run-1", suite_id: "labour", scored: true, agent: 0.42, judge: 0.18, total: 0.6, unpriced: [] }],
  plugins: { targets: ["python", "http", "command"], connectors: ["folder", "http"], providers: ["anthropic", "openai"] },
}

function serve(me: Me, view: SettingsView = VIEW) {
  const sent: { method: string; path: string; body: unknown }[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1")
      const method = init?.method ?? "GET"
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      const path = decodeURIComponent(url.pathname)
      sent.push({ method, path, body })
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      if (path === "/api/session") return reply({ role_locked: false })
      if (path === "/api/me") return reply(me)
      if (path === "/api/queue") return reply({ items: [] })
      if (path === "/api/settings") return reply(view)
      if (path.startsWith("/api/settings/sections/")) {
        const name = path.split("/").pop()!
        return reply({ ...view, sections: { ...view.sections, [name]: (body as { value: unknown }).value } })
      }
      if (path.startsWith("/api/settings/keys/"))
        return reply({ ...view, keys: [{ ...view.keys[0], where: "file", file: ".casebench/.env" }] })
      if (path === "/api/settings/check")
        return reply([{ part: "judge", status: "passed", passed: true, reason: "anthropic claude-judge answered", next: "" }])
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Deniz"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("settings", () => {
  test("settings show what is used for what", async () => {
    const user = userEvent.setup()
    serve(ENGINEER)
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Settings" }))
    const table = await screen.findByRole("table", { name: "What is used for what" })
    const judge = within(table).getByRole("row", { name: /judge/i })
    expect(within(judge).getByText(/anthropic · claude-judge/)).toBeInTheDocument()
    expect(within(judge).getByText("$3 / $15 per M tokens")).toBeInTheDocument()
    expect(within(judge).getByText(/reasoning effort low/)).toBeInTheDocument()
    expect(within(judge).getByText("ANTHROPIC_API_KEY not set")).toBeInTheDocument()
    expect(screen.getByText("$3.75")).toBeInTheDocument()
    expect(screen.getByText("run-1")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Check/ }))
    expect(await screen.findByText("anthropic claude-judge answered")).toBeInTheDocument()
  })

  test("a change is saved to casebench.yaml", async () => {
    const user = userEvent.setup()
    const sent = serve(ENGINEER)
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Settings" }))
    await user.click(await screen.findByRole("tab", { name: "Limits" }))
    const limit = screen.getByLabelText("Daily limit for trying questions (USD)")
    await user.clear(limit)
    await user.type(limit, "2.5")
    await user.click(screen.getByLabelText(/waits for a second editor/))
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(await screen.findByText("Limits saved to casebench.yaml")).toBeInTheDocument()
    const saved = sent.find((s) => s.method === "PUT")!
    expect(saved.path).toBe("/api/settings/sections/workbench")
    expect(saved.body).toEqual({ value: { try_daily_limit_usd: 2.5, second_approval: true } })
  })

  test("a key is set and never shown again", async () => {
    const user = userEvent.setup()
    const sent = serve(ENGINEER)
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Settings" }))
    await user.click(await screen.findByRole("tab", { name: "Keys" }))
    expect(screen.getByText("Not set")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Set" }))
    await user.type(screen.getByLabelText("Value of ANTHROPIC_API_KEY"), SECRET)
    await user.click(screen.getByRole("button", { name: "Save the key" }))
    expect(await screen.findByText(/Read from a file · \.casebench\/\.env/)).toBeInTheDocument()
    expect(sent.find((s) => s.path === "/api/settings/keys/ANTHROPIC_API_KEY")!.body).toEqual({ value: SECRET })
    expect(document.body.innerHTML).not.toContain(SECRET)
  })

  test("saving warns before comments are dropped", async () => {
    const user = userEvent.setup()
    const sent = serve(ENGINEER, { ...VIEW, has_comments: true })
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Settings" }))
    await user.click(await screen.findByRole("tab", { name: "Limits" }))
    await user.click(screen.getByLabelText(/waits for a second editor/))
    await user.click(screen.getByRole("button", { name: "Save" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("Comments in casebench.yaml will be dropped")).toBeInTheDocument()
    expect(sent.some((s) => s.method === "PUT")).toBe(false)
    await user.click(within(dialog).getByRole("button", { name: "Save anyway" }))
    await waitFor(() => expect(sent.filter((s) => s.method === "PUT")).toHaveLength(1))
  })

  test("a reviewer sees no settings", async () => {
    serve({ name: "Ayşe", view: "review", role_locked: true, role: "reviewer", setup: false })
    render(<App />)
    expect(await screen.findByRole("button", { name: /Review queue/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Settings" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Run" })).not.toBeInTheDocument()
  })
})

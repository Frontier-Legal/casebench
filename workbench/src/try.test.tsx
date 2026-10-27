// Try a question in the browser (decision 0052); the API is tested in
// tests/workbench/test_try_a_question.py.

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { Budget, Tried } from "@/lib/api"

const OPEN: Budget = {
  target: "firm-assistant",
  limit: 5,
  spent_today: 0.42,
  remaining: 4.58,
  can_ask: true,
  why_not: null,
  checks_citations: true,
}

const ANSWER: Tried = {
  question: "Is a dismissal by WhatsApp valid?",
  answer: "No. See Yargıtay 9. HD, E. 2023/1234 and Yargıtay 3. HD, E. 2021/999.",
  error: null,
  citations: [
    { citation: "Yargıtay 9. HD, E. 2023/1234", claim: "written notice", label: "verified", document_id: null, quote: null, reason: null },
    { citation: "Yargıtay 3. HD, E. 2021/999", claim: "see also", label: "fabricated", document_id: null, quote: null, reason: "no such decision" },
  ],
  agent_cost: 0.012,
  judge_cost: 0.004,
  cost: 0.016,
  unpriced: [],
  budget: { ...OPEN, spent_today: 0.436, remaining: 4.564 },
}

function serve(budget: Budget) {
  const sent: { method: string; path: string; body: unknown }[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1")
      const method = init?.method ?? "GET"
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      sent.push({ method, path: url.pathname, body })
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      const path = decodeURIComponent(url.pathname)
      if (path === "/api/session") return reply({ role_locked: false })
      if (path === "/api/me") return reply({ name: "Ayşe", view: "review", role_locked: false })
      if (path === "/api/queue") return reply({ items: [] })
      if (path === "/api/golden") return reply({ suites: [{ suite_id: "labour", cases: [] }], tasks: ["qa"], second_approval: false })
      if (path === "/api/golden/forms/qa")
        return reply(["question", "reference answer", "key points"].map((name) => ({ name, value: "", help: "" })))
      if (path === "/api/try" && method === "GET") return reply(budget)
      if (path === "/api/try" && method === "POST") return reply(ANSWER)
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Ayşe"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("try a question", () => {
  test("spot check to case", async () => {
    const user = userEvent.setup()
    const sent = serve(OPEN)
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Try a question/ }))
    expect(await screen.findByText("firm-assistant")).toBeInTheDocument()
    expect(screen.getByText("$4.58")).toBeInTheDocument()

    await user.type(screen.getByLabelText("Your question"), "Is a dismissal by WhatsApp valid?")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    const listed = await screen.findByRole("list", { name: "Citations" })
    expect(within(listed).getAllByRole("button").map((b) => b.getAttribute("data-citation"))).toEqual([
      "verified",
      "fabricated",
    ])
    expect(screen.getByText(/This question cost \$0\.02: the agent \$0\.01, the judge \$0\.0040/)).toBeInTheDocument()
    expect(sent.find((s) => s.method === "POST")!.body).toEqual({ question: "Is a dismissal by WhatsApp valid?" })

    await user.click(screen.getByRole("button", { name: /Save as case/ }))
    await user.click(await screen.findByRole("menuitem", { name: "labour" }))
    const sheet = await screen.findByRole("dialog")
    await waitFor(() =>
      expect(within(sheet).getByLabelText("Question")).toHaveValue("Is a dismissal by WhatsApp valid?"),
    )
  })

  test("asks for a question as the agent's users would ask it", async () => {
    const user = userEvent.setup()
    serve(OPEN)
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Try a question/ }))

    expect(await screen.findByText(/a question as your agent's users would ask it\./)).toBeInTheDocument()
    expect(screen.queryByText(/as a client would/)).not.toBeInTheDocument()
  })

  test("spend limit holds", async () => {
    const user = userEvent.setup()
    const sent = serve({
      ...OPEN,
      spent_today: 5,
      remaining: 0,
      can_ask: false,
      why_not: "today's limit of $5.00 is spent; it resets at midnight UTC",
    })
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Try a question/ }))

    expect(await screen.findByText("Nothing will be sent")).toBeInTheDocument()
    expect(screen.getByText(/Today's limit of \$5\.00 is spent/)).toBeInTheDocument()
    expect(screen.getByLabelText("Your question")).toBeDisabled()
    expect(screen.getByRole("button", { name: /Ask/ })).toBeDisabled()
    expect(sent.some((s) => s.method === "POST")).toBe(false)
  })
})

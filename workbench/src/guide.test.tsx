// A first-time engineer is guided through the setup, and Home says what is done and what is
// next (decision 0065); the API is tested in tests/workbench/test_setup_in_the_workbench.py.

import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "@/app"
import { reply, serveApi } from "@/test-api"
import { ENGINEER, JUDGE, settingsView } from "@/test-views"

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

test("a first visit is guided", async () => {
  let view = settingsView({})
  const sent = serveApi({
    "/api/session": () => ({ role_locked: false, setting_up: true }),
    "GET /api/me": () => reply({ detail: "no one by that name yet" }, 404),
    "PUT /api/me": (body) => ({ ...ENGINEER, name: (body as { name: string }).name }),
    "/api/settings": () => view,
    "/api/setup/scan": () => ({
      said: "read 3 Python files",
      entries: ["agent.py:answer"],
      clients: ["openai.OpenAI at agent.py:3"],
      models: ["gpt-4.1"],
    }),
    "PUT /api/settings/sections/target": (body) => {
      view = settingsView({ target: (body as { value: unknown }).value as Record<string, unknown> })
      return view
    },
    "/api/setup/agent-models": () => [{ model: "gpt-4.1", family: "gpt", price: { input: 2, output: 8 } }],
    "PUT /api/settings/sections/agent_models": () => view,
    "/api/queue": () => ({ items: [] }),
  })
  const user = userEvent.setup()
  render(<App />)

  expect(await screen.findByRole("heading", { name: "Welcome to Casebench" })).toBeInTheDocument()
  expect(screen.getByRole("radio", { name: /I build or run the AI system/ })).toBeChecked()
  await user.type(screen.getByLabelText("Your name"), "Deniz Kaya")
  await user.click(screen.getByRole("button", { name: "Start" }))

  expect(await screen.findByRole("heading", { name: "Let's set up Casebench, Deniz" })).toBeInTheDocument()
  expect(screen.getByRole("list", { name: "How Casebench works" })).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Start" }))

  // The one function the code scan found is offered first, and taken on Continue.
  const choice = await screen.findByRole("radio", { name: /agent\.py:answer/ })
  expect(choice).toHaveAttribute("aria-checked", "true")
  expect(screen.getByText("gpt-4.1")).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: /Continue/ }))

  expect(await screen.findByRole("heading", { name: "Jurisdictions" })).toBeInTheDocument()
  const saved = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/target")
  expect(saved?.body).toEqual({ value: { type: "python", entry: "agent.py:answer" } })
  // The agent's own models are read from its code and priced, as init writes them.
  const models = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/agent_models")
  expect(models?.body).toEqual({ value: [{ model: "gpt-4.1", family: "gpt" }] })
  expect(screen.getByRole("button", { name: /Skip for now/ })).toBeInTheDocument()
})

test("home says what is set up and what is next", async () => {
  const view = settingsView(
    {
      target: { type: "python", entry: "agent.py:answer" },
      corpora: { "fr-api": { connector: "http", jurisdictions: ["FR"], options: { base_url: "https://api.example/v1" } } },
      judges: [{ provider: "anthropic", model: "claude-judge" }],
    },
    [JUDGE],
    [{ name: "ANTHROPIC_API_KEY", where: "missing", file: null, used_by: ["judge"] }],
  )
  window.localStorage.setItem("casebench.person", "Deniz Kaya")
  serveApi({
    "/api/session": () => ({ role_locked: false }),
    "/api/me": () => ENGINEER,
    "/api/settings": () => view,
    "/api/runs": () => [],
    "/api/queue": () => ({ items: [] }),
  })
  render(<App />)

  expect(await screen.findByRole("heading", { name: "Welcome, Deniz" })).toBeInTheDocument()
  expect(screen.getByText("3 of 4 done")).toBeInTheDocument()
  expect(within(screen.getByRole("listitem", { name: "Jurisdictions" })).getByText("France")).toBeInTheDocument()
  expect(within(screen.getByRole("listitem", { name: "Keys" })).getByText(/ANTHROPIC_API_KEY not set/)).toBeInTheDocument()
  expect(screen.getByRole("button", { name: /Continue the setup guide/ })).toBeInTheDocument()
})

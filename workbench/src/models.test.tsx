// Each model Casebench calls is changed, tested and keyed on its own card, and a second judge
// is added from another family (decision 0065); the API is tested in
// tests/workbench/test_setup_in_the_workbench.py.

import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { ModelView } from "@/lib/api"
import { serveApi, type Sent } from "@/test-api"
import { ENGINEER, JUDGE, settingsView } from "@/test-views"

const JUDGE_BLOCK = { provider: "anthropic", model: "claude-judge", options: { api_key_env: "ANTHROPIC_API_KEY" } }
const GPT = { provider: "openai", model: "gpt-judge", options: { api_key_env: "OPENAI_API_KEY", family: "gpt" } }
const GPT_VIEW: ModelView = { ...JUDGE, role: "second judge", provider: "openai", model: "gpt-judge", family: "gpt", key: "OPENAI_API_KEY" }

let sent: Sent[]

beforeEach(() => {
  window.localStorage.setItem("casebench.person", "Deniz Kaya")
})
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

function serve() {
  let view = settingsView(
    { target: { type: "python", entry: "agent.py:answer" }, judges: [JUDGE_BLOCK] },
    [JUDGE],
    [{ name: "ANTHROPIC_API_KEY", where: "missing", file: null, used_by: ["judge"] }],
  )
  sent = serveApi({
    "/api/session": () => ({ role_locked: false }),
    "/api/me": () => ENGINEER,
    "/api/settings": () => view,
    "/api/runs": () => [],
    "/api/queue": () => ({ items: [] }),
    "/api/settings/catalog": () => [{ id: "openai", name: "OpenAI", models: 1 }],
    "/api/settings/catalog/openai": () => [
      { id: "gpt-judge", name: "GPT Judge", family: "gpt", price_input: 1.25, price_output: 10, context_window: 400000, max_output: 128000 },
    ],
    "POST /api/settings/catalog/model": () => ({ block: GPT, missing: [], plugins: [] }),
    "POST /api/setup/models/test": () => ({ part: "judge", status: "passed", passed: true, reason: "anthropic claude-judge answered", next: "" }),
    "PUT /api/settings/keys/ANTHROPIC_API_KEY": () => {
      view = { ...view, keys: [{ name: "ANTHROPIC_API_KEY", where: "file", file: ".env", used_by: ["judge"] }] }
      return view
    },
    "/api/setup/agent-models": () => [{ model: "gpt-4.1", family: "gpt", price: { input: 2, output: 8 } }],
    "PUT /api/settings/sections/agent_models": (body) => {
      const listed = (body as { value: { model: string; family: string }[] }).value
      // As the server answers: the agent's models priced from the sellers' lists (0069).
      view = {
        ...view,
        sections: { ...view.sections, agent_models: listed },
        agent_models: listed.map((m) => ({ ...m, price_input: 2, price_output: 8 })),
      }
      return view
    },
    "PUT /api/settings/sections/judges": (body) => {
      const judges = (body as { value: unknown[] }).value
      view = { ...view, sections: { ...view.sections, judges }, models: judges.length > 1 ? [JUDGE, GPT_VIEW] : [JUDGE] }
      return view
    },
  })
}

async function openModels(user: ReturnType<typeof userEvent.setup>) {
  render(<App />)
  await user.click(await screen.findByRole("button", { name: "Models" }))
  return await screen.findByRole("article", { name: "The judge" })
}

test("a model is tested and keyed on its own card", async () => {
  serve()
  const user = userEvent.setup()
  const card = await openModels(user)

  expect(within(card).getByText("ANTHROPIC_API_KEY is not set")).toBeInTheDocument()
  await user.click(within(card).getByRole("button", { name: /Set key/ }))
  await user.type(within(card).getByLabelText("Value of ANTHROPIC_API_KEY"), "sk-ant-0123456789")
  await user.click(within(card).getByRole("button", { name: "Save the key" }))
  expect(await within(card).findByText("ANTHROPIC_API_KEY is set")).toBeInTheDocument()

  await user.click(within(card).getByRole("button", { name: /Test this model/ }))
  expect(await within(card).findByText("It works")).toBeInTheDocument()
  const tested = sent.find((r) => r.path === "/api/setup/models/test")
  expect(tested?.body).toEqual({ block: JUDGE_BLOCK })
})

test("a second judge is added from the model catalog", async () => {
  serve()
  const user = userEvent.setup()
  await openModels(user)

  const empty = screen.getByLabelText("Second judge")
  expect(empty).toHaveTextContent(/another family than claude/)
  await user.click(within(empty).getByRole("button", { name: "Add a second judge" }))
  const dialog = await screen.findByRole("dialog")
  await user.click(await within(dialog).findByRole("combobox", { name: "Provider" }))
  await user.click(await screen.findByRole("option", { name: "OpenAI (1)" }))
  await user.click(await within(dialog).findByRole("button", { name: /GPT Judge/ }))
  await user.click(within(dialog).getByRole("button", { name: /Use this model/ }))

  expect(await screen.findByRole("article", { name: "Second judge" })).toBeInTheDocument()
  const saved = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/judges")
  expect(saved?.body).toEqual({ value: [JUDGE_BLOCK, GPT] })
})

test("the agent's models are read from its code", async () => {
  serve()
  const user = userEvent.setup()
  await openModels(user)

  await user.click(screen.getByRole("button", { name: /Read them from your code/ }))

  expect(await screen.findByRole("cell", { name: "gpt-4.1" })).toBeInTheDocument()
  expect(screen.getByRole("cell", { name: "$2 in · $8 out" })).toBeInTheDocument()
  const saved = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/agent_models")
  // Saved without a price: it is looked up, never written.
  expect(saved?.body).toEqual({ value: [{ model: "gpt-4.1", family: "gpt" }] })
})

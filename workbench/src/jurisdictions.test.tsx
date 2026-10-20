// A second jurisdiction is added from the browser: a country by name, then its source, with
// fields picked from real values (decision 0065); the API is tested in
// tests/workbench/test_setup_in_the_workbench.py.

import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { Connected } from "@/lib/api"
import { serveApi, type Sent } from "@/test-api"
import { ENGINEER, settingsView } from "@/test-views"

const TR = { connector: "http", jurisdictions: ["TR"], options: { base_url: "https://tr.example/v1" } }
const SEARCHED: Connected = {
  name: "api-example",
  results: "$.results[*]",
  result_choices: [
    { path: "$.work.work_id", value: "c-2024-1" },
    { path: "$.citation", value: "Cass. soc., 12 mars 2024" },
  ],
  document_choices: [],
  fields: {},
  missing: [],
  block: null,
}
const BLOCK = { connector: "http", jurisdictions: ["FR"], options: { base_url: "https://api.example/v1" }, probe: "licenciement" }

let sent: Sent[]

function serve(connect: (body: Record<string, unknown>) => Connected, path = "/api/setup/sources/api") {
  let view = settingsView({ target: { type: "python", entry: "agent.py:answer" }, corpora: { "tr-api": TR } })
  sent = serveApi({
    "/api/session": () => ({ role_locked: false }),
    "/api/me": () => ENGINEER,
    "/api/settings": () => view,
    "/api/runs": () => [],
    "/api/queue": () => ({ items: [] }),
    "/api/setup/jurisdictions": () => ["DE", "FR", "TR", "EU"],
    [path]: (body) => connect(body as Record<string, unknown>),
    "/api/setup/sources/mcp/tools": () => [
      { name: "search", description: "Find decisions" },
      { name: "get_document", description: "One document in full" },
    ],
    "PUT /api/settings/sections/corpora": (body) => {
      view = settingsView({ ...view.sections, corpora: (body as { value: Record<string, unknown> }).value })
      return view
    },
  })
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Deniz Kaya"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

async function openFrance(user: ReturnType<typeof userEvent.setup>) {
  render(<App />)
  await user.click(await screen.findByRole("button", { name: "Jurisdictions" }))
  expect(await screen.findByRole("article", { name: "Türkiye" })).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Add a jurisdiction" }))
  await user.type(await screen.findByLabelText("Find a country"), "fran")
  await user.click(await screen.findByRole("button", { name: /France/ }))
}

test("a jurisdiction is added from a document API", async () => {
  serve((body) => ((body.result_fields as Record<string, string>)?.id ? { ...SEARCHED, block: BLOCK, document_choices: [{ path: "$.text", value: "Le licenciement…" }], fields: { text: "$.text" } } : SEARCHED))
  const user = userEvent.setup()
  await openFrance(user)

  const choices = screen.getAllByRole("radio").map((r) => r.textContent)
  // A provider's or the firm's API comes first; sample files last.
  expect(choices[0]).toMatch(/A document API/)
  expect(choices.findIndex((c) => /sample documents/.test(c ?? ""))).toBeGreaterThan(2)
  await user.click(screen.getByRole("radio", { name: /A document API/ }))
  await user.type(screen.getByLabelText("The API's address"), "https://api.example/v1")
  await user.type(screen.getByLabelText("A search that finds a document"), "licenciement")
  await user.click(screen.getByRole("button", { name: /Search the source/ }))

  const result = await screen.findByRole("region", { name: "A search result" })
  await user.selectOptions(within(result).getByLabelText(/The document's id/), "$.work.work_id")
  await user.click(within(result).getByRole("button", { name: /Fetch that document/ }))
  expect(await screen.findByRole("region", { name: "The document" })).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Add France" }))

  expect(await screen.findByRole("article", { name: "France" })).toBeInTheDocument()
  const asked = sent.filter((r) => r.path === "/api/setup/sources/api").at(-1)?.body as Record<string, unknown>
  expect(asked.jurisdictions).toEqual(["FR"])
  expect(asked.result_fields).toEqual({ id: "$.work.work_id" })
  const saved = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/corpora")
  expect(saved?.body).toEqual({ value: { "tr-api": TR, "api-example": BLOCK } })
})

test("a jurisdiction is added from an MCP server", async () => {
  const mcp = { ...BLOCK, connector: "mcp", options: { command: ["legal-docs-mcp"] } }
  serve((body) => ((body.result_fields as Record<string, string>)?.id ? { ...SEARCHED, name: "legal-docs-mcp", block: mcp } : SEARCHED), "/api/setup/sources/mcp")
  const user = userEvent.setup()
  await openFrance(user)

  await user.click(screen.getByRole("radio", { name: /An MCP server/ }))
  await user.type(screen.getByLabelText("How to reach the server"), "legal-docs-mcp")
  await user.click(screen.getByRole("button", { name: /List its tools/ }))
  await user.selectOptions(await screen.findByLabelText("The tool that searches"), "search")
  await user.selectOptions(screen.getByLabelText("The tool that returns a document"), "get_document")
  await user.type(screen.getByLabelText("A search that finds a document"), "licenciement")
  await user.click(screen.getByRole("button", { name: /Search the source/ }))
  const result = await screen.findByRole("region", { name: "A search result" })
  await user.selectOptions(within(result).getByLabelText(/The document's id/), "$.work.work_id")
  await user.click(within(result).getByRole("button", { name: /Fetch that document/ }))
  await user.click(await screen.findByRole("button", { name: "Add France" }))

  const asked = sent.filter((r) => r.path === "/api/setup/sources/mcp").at(-1)?.body as Record<string, unknown>
  expect(asked).toMatchObject({ command: "legal-docs-mcp", search_tool: "search", fetch_tool: "get_document" })
  const saved = sent.find((r) => r.method === "PUT" && r.path === "/api/settings/sections/corpora")
  expect(saved?.body).toEqual({ value: { "tr-api": TR, "legal-docs-mcp": mcp } })
})

// Two runs compared blind in the browser (decision 0054); the API is tested in
// tests/workbench/test_blind_comparison.py.

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { AreaView, Comparison, Pair } from "@/lib/api"

const RUNS = [
  { run_id: "r2", suite_id: "labour", target: "agent", scored: true },
  { run_id: "r1", suite_id: "labour", target: "agent", scored: true },
]

function pairOf(caseId: string, given: Pair["given"] = null): Pair {
  return {
    case_id: caseId,
    repeat: 0,
    title: `Was dismissal ${caseId} valid?`,
    inputs: [{ name: "question", text: `Was dismissal ${caseId} valid?` }],
    reference: [
      { id: "outcome-1", kind: "outcome", value: "upheld", document: "corpus:tr-1", quote: "kararı onamıştır", note: null, document_id: null, highlight: null },
    ],
    a: `One answer to ${caseId}.`,
    b: `Another answer to ${caseId}.`,
    given,
  }
}

const LABOUR: AreaView = {
  practice_area: "labour",
  n: 1,
  wins: 1,
  losses: 0,
  ties: 0,
  mean: 1,
  low: 1,
  high: 1,
  sign_p: 1,
  significant: false,
}

function serve() {
  const sent: { method: string; path: string; body: unknown }[] = []
  let given: Pair["given"] = null
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1")
      const method = init?.method ?? "GET"
      const path = decodeURIComponent(url.pathname)
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      sent.push({ method, path, body })
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      if (path === "/api/session") return reply({ role_locked: false })
      if (path === "/api/me") return reply({ name: "Ayşe", view: "review", role_locked: false })
      if (path === "/api/queue") return reply({ items: [] })
      if (path === "/api/runs") return reply(RUNS)
      if (path === "/api/compare/r1/r2") {
        const comparison: Comparison = {
          first: "r1",
          second: "r2",
          suite_id: "labour",
          pairs: [
            { case_id: "c1", repeat: 0, title: "Was dismissal c1 valid?", practice_area: "labour", given: given !== null },
            { case_id: "c2", repeat: 0, title: "Was dismissal c2 valid?", practice_area: "labour", given: false },
          ],
          areas: given ? [LABOUR] : [],
        }
        return reply(comparison)
      }
      if (path === "/api/compare/r1/r2/c1/0" && method === "POST") {
        given = { choice: "b", reason: body.reason, by: "Ayşe", at: "2026-10-15T12:00:00+00:00", a_run: "r1", b_run: "r2" }
        return reply(pairOf("c1", given))
      }
      if (path === "/api/compare/r1/r2/c1/0") return reply(pairOf("c1", given))
      if (path === "/api/compare/r1/r2/c2/0") return reply(pairOf("c2"))
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

describe("compare runs", () => {
  test("blind A/B", async () => {
    const user = userEvent.setup()
    const sent = serve()
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Compare runs/ }))

    // The two latest runs of one suite are chosen, and the first pair is shown as A and B.
    const answers = await screen.findByLabelText("Answers")
    expect(within(answers).getByText("One answer to c1.")).toBeInTheDocument()
    expect(within(answers).getByText("Another answer to c1.")).toBeInTheDocument()
    expect(screen.getByText("Pair 1 of 2")).toBeInTheDocument()
    expect(screen.queryByText(/run r2/)).not.toBeInTheDocument()

    // A reason is required; the keyboard chooses.
    await user.keyboard("b")
    expect(screen.getByRole("radio", { name: "B is better" })).toHaveAttribute("data-state", "on")
    await user.keyboard("{Control>}{Enter}{/Control}")
    expect(screen.getByText(/Say why/)).toBeInTheDocument()
    expect(sent.some((s) => s.method === "POST")).toBe(false)

    await user.type(screen.getByLabelText("Why?"), "B cites the article in force")
    await user.keyboard("{Control>}{Enter}{/Control}")
    await waitFor(() => expect(screen.getByText("Pair 2 of 2")).toBeInTheDocument())
    expect(sent.find((s) => s.method === "POST")).toEqual({
      method: "POST",
      path: "/api/compare/r1/r2/c1/0",
      body: { choice: "b", reason: "B cites the article in force" },
    })

    // The later run's wins per practice area, not significant on one pair.
    const table = await screen.findByRole("table", { name: "Preferences by practice area" })
    const [, row] = within(table).getAllByRole("row")
    expect(within(row).getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "labour",
      "1",
      "0",
      "0",
      "+1.00 [+1.00, +1.00]",
      "Not significant",
    ])

    // Back on the first pair, the runs are named.
    await user.click(screen.getByRole("button", { name: "Previous pair" }))
    expect(await screen.findByText(/A was run r1 \(earlier\); B was run r2 \(later\)/)).toBeInTheDocument()
  })
})

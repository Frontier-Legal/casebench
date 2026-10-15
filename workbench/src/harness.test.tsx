// The harness view in the browser (decision 0056); the API is tested in
// tests/workbench/test_harness_view.py.

import { render, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { AnswerItem, Harness, View } from "@/lib/api"

const KEY = "answer:r1:c1:0"

const ITEM: AnswerItem = {
  key: KEY,
  kind: "answer",
  title: "Is the dismissal valid?",
  where: "run r1",
  task: "qa",
  inputs: [{ name: "question", text: "Is the dismissal valid?" }],
  answer: "Invalid, see m. 18.",
  reference: [],
  criteria: [],
  citations: [],
  scores: [],
  draft: null,
  held_by: null,
  engineering: null,
}

const HARNESS: Harness = {
  run_id: "r1",
  case_id: "c1",
  repeat: 0,
  latency_ms: 6000,
  span_ms: 5400,
  unaccounted_ms: 3800,
  outside_ms: 600,
  bars: [
    { number: 1, kind: "llm", name: "think 4", model: "agent-model", at_ms: 0, duration_ms: 1000, input_tokens: 3000, output_tokens: 300, cost: 0.0135, arguments: null, unaccounted: false },
    { number: 2, kind: "gap", name: "between think 4 and think 5", model: null, at_ms: 1000, duration_ms: 3200, input_tokens: null, output_tokens: null, cost: null, arguments: null, unaccounted: true },
    { number: 3, kind: "llm", name: "think 5", model: "agent-model", at_ms: 4200, duration_ms: 1200, input_tokens: 3000, output_tokens: 300, cost: 0.0135, arguments: null, unaccounted: false },
  ],
  untimed: 0,
  by_step: [],
  by_model: [],
  priced: true,
  funnel: null,
  funnel_possible: true,
  against: null,
  diff: [],
  funnel_before: null,
}

function serve(view: View) {
  const sent: string[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1")
      const path = decodeURIComponent(url.pathname)
      sent.push(`${init?.method ?? "GET"} ${path}`)
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      if (path === "/api/session") return reply({ role_locked: false })
      if (path === "/api/me") return reply({ name: "Emre", view, role_locked: false })
      if (path === "/api/queue")
        return reply({ items: [{ key: KEY, kind: "answer", title: ITEM.title, where: "run r1", task: "qa", flags: [] }] })
      if (path === `/api/items/${KEY}/reserve`) return reply({ held_by: "Emre" })
      if (path === `/api/items/${KEY}`)
        return reply(
          view === "engineering"
            ? { ...ITEM, engineering: { latency_ms: 6000, input_tokens: 6000, output_tokens: 600, cost: 0.027, steps: [], raw: {} } }
            : ITEM,
        )
      if (path === "/api/runs") return reply([{ run_id: "r1", suite_id: "labour", target: "agent", scored: true }])
      if (path === "/api/harness/r1/c1/0") return reply(HARNESS)
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Emre"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("harness view", () => {
  test("waterfall with honest gaps", async () => {
    serve("engineering")
    render(<App />)

    const waterfall = await screen.findByRole("list", { name: "Waterfall" })
    const rows = within(waterfall).getAllByRole("listitem")
    expect(rows.map((r) => r.hasAttribute("data-unaccounted"))).toEqual([false, true, false, true])
    expect(rows[1]).toHaveTextContent("Unaccounted")
    expect(rows[1]).toHaveTextContent("3.20 s")
    expect(rows[0]).toHaveTextContent("≈ $0.01")
    expect(rows[3]).toHaveTextContent("600 ms")
  })

  test("hidden from reviewers", async () => {
    const sent = serve("review")
    render(<App />)

    expect(await screen.findByText("Invalid, see m. 18.")).toBeInTheDocument()
    expect(screen.queryByTestId("harness")).not.toBeInTheDocument()
    expect(sent.some((s) => s.includes("/api/harness"))).toBe(false)
  })
})

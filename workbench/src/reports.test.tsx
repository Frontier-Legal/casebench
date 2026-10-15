// A run's error rates in the browser (decision 0054); the API is tested in
// tests/workbench/test_partner_report.py.

import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { AnswerItem, RunReport } from "@/lib/api"

const KEY = "answer:r1:c1:0"

const REPORT: RunReport = {
  run_id: "r1",
  suite_id: "labour",
  target: "firm-assistant",
  rates: [
    {
      error: "fabricated citation",
      meaning: "cites a decision or statute the corpus does not hold",
      n: 4,
      rate: 0.25,
      low: 0,
      high: 0.75,
      failing: [{ key: KEY, case_id: "c1", repeat: 0, title: "Was dismissal c1 valid?" }],
    },
    {
      error: "wrong statute",
      meaning: "relies on a statute the court did not apply",
      n: 4,
      rate: 0,
      low: 0,
      high: 0,
      failing: [],
    },
  ],
}

const ANSWER: AnswerItem = {
  key: KEY,
  kind: "answer",
  title: "Was dismissal c1 valid?",
  where: "run r1",
  task: "qa",
  inputs: [{ name: "question", text: "Was dismissal c1 valid?" }],
  answer: "No, see Yargıtay 3. HD, E. 2021/999.",
  reference: [
    { id: "outcome-1", kind: "outcome", value: "upheld", document: "corpus:tr-1", quote: "kararı onamıştır", note: null, document_id: null, highlight: null },
  ],
  criteria: [],
  citations: [
    { citation: "Yargıtay 3. HD, E. 2021/999", claim: "see also", label: "fabricated", document_id: null, quote: null, reason: "no such decision" },
  ],
  scores: [],
  draft: null,
  held_by: null,
  engineering: null,
}

function serve() {
  const sent: string[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1")
      const method = init?.method ?? "GET"
      const path = decodeURIComponent(url.pathname)
      sent.push(`${method} ${path}`)
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      if (path === "/api/session") return reply({ role_locked: false })
      if (path === "/api/me") return reply({ name: "Ayşe", view: "review", role_locked: false })
      if (path === "/api/queue") return reply({ items: [] })
      if (path === "/api/runs") return reply([{ run_id: "r1", suite_id: "labour", target: "firm-assistant", scored: true }])
      if (path === "/api/runs/r1/report") return reply(REPORT)
      if (path === `/api/items/${KEY}/reserve`) return reply({ held_by: "Ayşe" })
      if (path === `/api/items/${KEY}`) return reply(ANSWER)
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

describe("reports", () => {
  test("error breakdown", async () => {
    const user = userEvent.setup()
    const sent = serve()
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Reports/ }))

    const rates = await screen.findByLabelText("Error rates")
    const cards = within(rates).getAllByRole("button")
    expect(cards.map((c) => c.textContent)).toEqual([
      expect.stringMatching(/^fabricated citation25%1 of 4 answers · 95% interval 0% to 75%/),
      expect.stringMatching(/^wrong statute0%0 of 4 answers/),
    ])
    expect(cards[0]).toHaveAttribute("aria-pressed", "true")

    const listed = screen.getByRole("list", { name: "Answers with fabricated citation" })
    await user.click(within(listed).getByRole("button", { name: /Was dismissal c1 valid\?/ }))

    // The failing answer opens beside its evidence, as in answer review.
    expect(await screen.findByText("Answer · run r1")).toBeInTheDocument()
    expect(sent).toContain(`POST /api/items/${KEY}/reserve`)
    const cited = screen.getAllByRole("button", { name: /Yargıtay 3\. HD, E\. 2021\/999/ })
    expect(cited.map((b) => b.getAttribute("data-citation"))).toContain("fabricated")
    expect(screen.getByText("“kararı onamıştır”")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Reports/ }))
    await user.click(within(await screen.findByLabelText("Error rates")).getAllByRole("button")[1])
    expect(screen.getByText("None of the 4 answers has this error.")).toBeInTheDocument()
  })
})

// The review queue in the browser (decision 0050). The other scenarios are tested against the
// API in tests/workbench/test_review_queue.py.

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { AnswerItem, CitationView, DraftItem, Engineering, QueueItem } from "@/lib/api"

interface Sent {
  method: string
  path: string
  body: unknown
}

const ENGINEERING: Engineering = {
  latency_ms: 1840,
  input_tokens: 812,
  output_tokens: 95,
  steps: [{ kind: "llm", name: "draft answer", model: "agent-model", duration_ms: 1700, input_tokens: 812, output_tokens: 95 }],
  raw: { result: { output: "…" } },
}

function answer(n: number, extra: Partial<AnswerItem> = {}): AnswerItem {
  return {
    key: `answer:r1:case-${n}:0`,
    kind: "answer",
    title: `Question ${n}: is the dismissal valid?`,
    where: "run r1",
    task: "qa",
    inputs: [{ name: "question", text: `Question ${n}: is the dismissal valid?` }],
    answer: "The dismissal is invalid under İş Kanunu m. 18.",
    reference: [],
    criteria: [
      {
        id: "c1",
        text: "Relies on İş Kanunu m. 18",
        weight: 3,
        kind: "statute",
        judge: "pass",
        judge_quote: "İş Kanunu m. 18",
        judge_note: null,
        evidence: ["4857 sayılı İş Kanunu m. 18"],
        lawyer: null,
        judges_disagreed: false,
      },
    ],
    citations: [],
    scores: [{ metric: "criteria", value: 1, label: "all criteria passed" }],
    draft: null,
    held_by: null,
    engineering: null,
    ...extra,
  }
}

const CITATIONS: CitationView[] = [
  { citation: "Yargıtay 9. HD, E. 2023/1234", claim: "valid reason", label: "verified", document_id: "corpus:tr-1", quote: "geçerli sebebe dayanmalıdır", reason: null },
  { citation: "İş Kanunu m. 21", claim: "reinstatement", label: "verified", document_id: "corpus:tr-1", quote: "işe iade", reason: null },
  { citation: "Yargıtay 22. HD, E. 2022/77", claim: "invalid", label: "misgrounded", document_id: "corpus:tr-2", quote: null, reason: "the passage says something else" },
  { citation: "Yargıtay 3. HD, E. 2021/999", claim: "see also", label: "fabricated", document_id: null, quote: null, reason: "no such decision" },
]

const DRAFT: DraftItem = {
  key: "draft:drafts:draft-1",
  kind: "draft",
  title: "How did the court rule?",
  where: "suite drafts",
  task: "outcome",
  inputs: [],
  decision: { id: "corpus:tr-1", court: "Yargıtay 9. HD", date: "2020-03-01", text: "Daire kararı onamıştır. 4857 sayılı İş Kanunu m. 18 uygulanır." },
  facts: [
    { id: "outcome-1", kind: "outcome", value: "upheld", document: "corpus:tr-1", quote: "kararı onamıştır", note: null, document_id: null, highlight: { start: 6, end: 22 } },
    { id: "statute-1", kind: "statute", value: "4857 sayılı İş Kanunu m. 18", document: "corpus:tr-1", quote: "4857 sayılı İş Kanunu m. 18", note: null, document_id: null, highlight: { start: 24, end: 51 } },
  ],
  draft: null,
  held_by: null,
  engineering: null,
}

/** A workbench API in memory: the queue shrinks as items are finished. */
function serve(items: (AnswerItem | DraftItem)[], view: "review" | "engineering" = "review") {
  const sent: Sent[] = []
  const left = [...items]
  const queued = (): QueueItem[] =>
    left.map((i) => ({ key: i.key, kind: i.kind, title: i.title, where: i.where, task: i.task, flags: [] }))
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://127.0.0.1")
    const method = init?.method ?? "GET"
    const body = init?.body ? JSON.parse(String(init.body)) : undefined
    sent.push({ method, path: url.pathname, body })
    const reply = (value: unknown, status = 200) =>
      new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
    const path = decodeURIComponent(url.pathname)
    if (path === "/api/session") return reply({ role_locked: false })
    if (path === "/api/me") return reply({ name: "Ayşe", view, role_locked: false })
    if (path === "/api/queue") return reply({ items: queued() })
    if (path.startsWith("/api/documents/"))
      return reply({ id: "corpus:tr-1", court: "Yargıtay 9. HD", date: "2020-03-01", text: "Fesih geçerli sebebe dayanmalıdır.", highlight: { start: 6, end: 33 } })
    const match = path.match(/^\/api\/items\/(.+?)(\/(reserve|draft|finish))?$/)
    if (match) {
      const found = left.find((i) => i.key === match[1])
      if (!found) return reply({ detail: "no such item" }, 404)
      if (match[3] === "finish") {
        left.splice(left.indexOf(found), 1)
        return reply({ key: found.key, message: "recorded" })
      }
      if (match[3]) return reply({ held_by: "Ayşe" })
      return reply(found)
    }
    return reply({ detail: "not found" }, 404)
  })
  vi.stubGlobal("fetch", fetcher)
  return sent
}

const finished = (sent: Sent[]) => sent.filter((s) => s.path.endsWith("/finish"))

beforeEach(() => window.localStorage.setItem("casebench.person", "Ayşe"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("the review queue", () => {
  test("keyboard first", async () => {
    const user = userEvent.setup()
    const sent = serve(Array.from({ length: 30 }, (_, n) => answer(n + 1)))
    render(<App />)
    await screen.findByRole("heading", { name: /Question 1:/ })

    // 1 keeps the judge's pass; Cmd+Enter finishes, and the next item opens without a click.
    await user.keyboard("1")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    await screen.findByRole("heading", { name: /Question 2:/ })
    expect(finished(sent)[0].body).toEqual({
      verdicts: [{ criterion_id: "c1", verdict: "pass", note: null }],
    })

    // 2 overrules the judge, which needs a note before the item can finish.
    await user.keyboard("2")
    expect(screen.getByLabelText(/Why do you overrule the judge/)).toHaveFocus()
    await user.keyboard("{Control>}{Enter}{/Control}")
    expect(await screen.findByText("Say why before you finish.")).toBeInTheDocument()
    expect(finished(sent)).toHaveLength(1)
    await user.keyboard("Cited for the wrong proposition.")
    await user.keyboard("{Control>}{Enter}{/Control}")
    await screen.findByRole("heading", { name: /Question 3:/ })
    expect(finished(sent)[1].body).toEqual({
      verdicts: [{ criterion_id: "c1", verdict: "fail", note: "Cited for the wrong proposition." }],
    })

    // ? lists the shortcuts.
    await user.keyboard("?")
    const dialog = await screen.findByRole("dialog", { name: "Keyboard shortcuts" })
    const listed = within(dialog).getByRole("list", { name: "Shortcuts" })
    expect(within(listed).getAllByRole("listitem").map((li) => li.textContent)).toEqual(
      expect.arrayContaining([
        expect.stringContaining("Pick the numbered choice"),
        expect.stringContaining("Finish and open the next item"),
        expect.stringContaining("Show these shortcuts"),
      ]),
    )
  })

  test("no engineering on screen", async () => {
    serve([answer(1)], "review")
    const { unmount } = render(<App />)
    await screen.findByRole("heading", { name: /Question 1:/ })
    expect(screen.queryByTestId("engineering")).not.toBeInTheDocument()
    expect(screen.queryByText(/tokens/i)).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/[{}]/)
    unmount()
    vi.unstubAllGlobals()

    serve([answer(1, { engineering: ENGINEERING })], "engineering")
    render(<App />)
    const card = await screen.findByTestId("engineering")
    expect(within(card).getByText("Input tokens")).toBeInTheDocument()
    expect(within(card).getByText("agent-model")).toBeInTheDocument()
  })

  test("citations coloured by what the corpus says", async () => {
    const user = userEvent.setup()
    serve([answer(1, { answer: CITATIONS.map((c) => c.citation).join("; "), citations: CITATIONS })])
    render(<App />)
    await screen.findByRole("heading", { name: /Question 1:/ })

    const listed = screen.getByRole("list", { name: "Citations" })
    const labels = within(listed)
      .getAllByRole("button")
      .map((b) => b.getAttribute("data-citation"))
    expect(labels).toEqual(["verified", "verified", "misgrounded", "fabricated"])
    const marked = [...document.querySelectorAll("mark[data-tone][role=button]")].map((m) => m.getAttribute("data-tone"))
    expect(marked).toEqual(["verified", "verified", "misgrounded", "fabricated"])

    await user.click(within(listed).getAllByRole("button")[0])
    const source = await screen.findByTestId("source-panel")
    await waitFor(() =>
      expect(within(source).getByText("geçerli sebebe dayanmalıdır", { selector: "mark" })).toBeInTheDocument(),
    )
  })

  test("approve a court draft with one key per fact", async () => {
    const user = userEvent.setup()
    const sent = serve([DRAFT])
    render(<App />)
    await screen.findByRole("heading", { name: "How did the court rule?" })
    expect(document.querySelectorAll('mark[data-tone="passage"]')).toHaveLength(2)

    await user.keyboard("1")
    await user.keyboard("2")
    const value = screen.getByLabelText("The fact as it should read")
    await user.clear(value)
    await user.type(value, "4857 sayılı İş Kanunu m. 18/1")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    expect(await screen.findByText("Say why you changed it.")).toBeInTheDocument()
    expect(finished(sent)).toHaveLength(0)
    await user.type(screen.getByLabelText(/Why do you change it/), "Only the first paragraph applies.")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    await waitFor(() => expect(finished(sent)).toHaveLength(1))
    expect(finished(sent)[0].body).toEqual({
      facts: [
        { fact_id: "outcome-1", decision: "approve" },
        { fact_id: "statute-1", decision: "edit", value: "4857 sayılı İş Kanunu m. 18/1", reason: "Only the first paragraph applies." },
      ],
    })
  })
})

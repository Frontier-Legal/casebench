// Golden data in the browser (decision 0052); the API is tested in
// tests/workbench/test_golden_data.py.

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { CaseDetail, ChangeItem, FormField, Golden } from "@/lib/api"

interface Sent {
  method: string
  path: string
  body: unknown
}

const CHANGE: ChangeItem = {
  key: "change:7",
  kind: "change",
  title: "Is notice required before dismissing for a valid reason?",
  where: "suite labour",
  task: "qa",
  proposal: { id: 7, kind: "change", author: "Ayşe", at: "2026-10-15T09:30:00Z", reason: "statute amended in 2025" },
  changes: [
    { field: "reference answer", before: "Yes: m. 17 notice periods apply.", after: "Yes, but the 2025 amendment shortens them." },
  ],
  draft: null,
  held_by: null,
  engineering: null,
}

const GOLDEN: Golden = {
  suites: [
    {
      suite_id: "labour",
      cases: [
        { case_id: "labour-1", title: "Is notice required?", task: "qa", source: "lawyer", approval: "approved", editable: true, waiting: null },
      ],
    },
  ],
  tasks: ["qa", "research", "drafting"],
}

const BLANK: FormField[] = ["question", "facts", "reference answer", "key points", "statutes", "precedents"].map(
  (name) => ({ name, value: "", help: "" }),
)

function serve(queue: ChangeItem[]) {
  const sent: Sent[] = []
  const left = [...queue]
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
      if (path === "/api/me") return reply({ name: "Can", view: "review", role_locked: false })
      if (path === "/api/queue")
        return reply({ items: left.map((i) => ({ key: i.key, kind: i.kind, title: i.title, where: i.where, task: i.task, flags: ["change"] })) })
      if (path === "/api/golden") return reply(GOLDEN)
      if (path === "/api/golden/forms/qa") return reply(BLANK)
      if (path === "/api/golden/labour" && method === "POST")
        return reply({ suite_id: "labour", case_id: "labour-2", proposal: 8, message: "labour-2 is a draft" })
      if (path === "/api/golden/labour/labour-1")
        return reply({ ...GOLDEN.suites[0].cases[0], suite_id: "labour", author: "Ayşe", fields: BLANK } as CaseDetail)
      const match = path.match(/^\/api\/items\/(.+?)(\/(reserve|draft|finish))?$/)
      if (match) {
        const found = left.find((i) => i.key === match[1])
        if (!found) return reply({ detail: "no such item" }, 404)
        if (match[3] === "finish") {
          left.splice(left.indexOf(found), 1)
          return reply({ key: found.key, message: "rejected" })
        }
        if (match[3]) return reply({ held_by: "Can" })
        return reply(found)
      }
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Can"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("golden data", () => {
  test("four-eye approval", async () => {
    const user = userEvent.setup()
    const sent = serve([CHANGE])
    render(<App />)
    await screen.findByRole("heading", { name: CHANGE.title })

    // The second editor sees the change, the author and the reason.
    expect(screen.getByText("Yes: m. 17 notice periods apply.")).toBeInTheDocument()
    expect(screen.getByText("Yes, but the 2025 amendment shortens them.")).toBeInTheDocument()
    expect(screen.getByText("statute amended in 2025")).toBeInTheDocument()
    expect(screen.getAllByText("Ayşe").length).toBeGreaterThan(0)

    // Rejecting needs a note.
    await user.keyboard("2")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    expect(await screen.findByText("Say why you reject it; its author reads it.")).toBeInTheDocument()
    expect(sent.some((s) => s.path.endsWith("/finish"))).toBe(false)
    await user.type(screen.getByLabelText("Why do you reject it?"), "The amendment applies from 2026.")
    await user.keyboard("{Meta>}{Enter}{/Meta}")
    await waitFor(() => expect(sent.some((s) => s.path.endsWith("/finish"))).toBe(true))
    expect(sent.find((s) => s.path.endsWith("/finish"))!.body).toEqual({
      decision: "reject",
      note: "The amendment applies from 2026.",
    })
  })

  test("new case from the form", async () => {
    const user = userEvent.setup()
    const sent = serve([])
    render(<App />)
    await user.click(await screen.findByRole("button", { name: /Golden data/ }))
    expect(await screen.findByText("Is notice required?")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "New case" }))
    const sheet = await screen.findByRole("dialog")
    await user.type(await within(sheet).findByLabelText("Question"), "Can an employer dismiss by text message?")
    await user.type(within(sheet).getByLabelText("Key points"), "+5 Says written notice is required")
    await user.click(within(sheet).getByRole("button", { name: "Save as draft" }))

    await waitFor(() => expect(sent.some((s) => s.method === "POST" && s.path === "/api/golden/labour")).toBe(true))
    const posted = sent.find((s) => s.method === "POST" && s.path === "/api/golden/labour")!.body as {
      task: string
      fields: Record<string, string>
    }
    expect(posted.task).toBe("qa")
    expect(posted.fields.question).toBe("Can an employer dismiss by text message?")
    expect(posted.fields["key points"]).toBe("+5 Says written notice is required")
  })
})

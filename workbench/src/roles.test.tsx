// The web app hides what the caller's role cannot do (decision 0058); the API refuses it, as
// tests/workbench/test_team_hooks.py shows.

import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { AnswerItem } from "@/lib/api"

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

function serve(can: string[]) {
  const sent: string[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = decodeURIComponent(new URL(String(input), "http://127.0.0.1").pathname)
      sent.push(`${init?.method ?? "GET"} ${path}`)
      const reply = (value: unknown, status = 200) =>
        new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
      // A team server: no name is typed, the server knows who is calling.
      if (path === "/api/session") return reply({ role_locked: false, mode: "team" })
      if (path === "/api/me")
        return reply({ name: "Deniz", view: "review", role_locked: true, role: "viewer", can })
      if (path === "/api/queue")
        return reply({ items: [{ key: KEY, kind: "answer", title: ITEM.title, where: "run r1", task: "qa", flags: [] }] })
      if (path === `/api/items/${KEY}/reserve`) return reply({ held_by: "Deniz" })
      if (path === `/api/items/${KEY}`) return reply(ITEM)
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("roles", () => {
  test("a viewer reads and does not act", async () => {
    const sent = serve(["read"])
    render(<App />)

    expect(await screen.findByText(/Your role lets you read this item/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Finish and next/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Try a question/ })).not.toBeInTheDocument()
    expect(sent).not.toContain(`POST /api/items/${KEY}/reserve`)
  })

  test("a reviewer gives verdicts", async () => {
    const sent = serve(["read", "review", "compare", "try"])
    render(<App />)

    expect(await screen.findByRole("button", { name: /Finish and next/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Try a question/ })).toBeInTheDocument()
    expect(sent).toContain(`POST /api/items/${KEY}/reserve`)
  })
})

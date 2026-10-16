// The Run page in the browser (decision 0063); the API is tested in
// tests/workbench/test_run_from_the_workbench.py.

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { JobView } from "@/lib/api"

const PLAN = {
  lines: ["target: 3 calls (0 cases already stored), about 120 input tokens", "nothing was sent"],
  can_start: true,
  why_not: null,
}

function job(state: JobView["state"], unscored = 0): JobView {
  return {
    id: "job-1",
    title: "suite outcomes",
    suite_id: "outcomes",
    state,
    started_at: "2026-10-16T10:00:00Z",
    finished_at: state === "running" ? null : "2026-10-16T10:01:00Z",
    exit_code: state === "running" ? null : 0,
    run_id: "20261016T100000Z-abc",
    answered: 3,
    scored: 3,
    total: 3,
    unscored,
    line_count: 2,
    lines: ["answered 3/3 case-002 in 0.1s", "scored 3/3 case-002 in 0.1s, judge $0.01 so far"],
  }
}

function serve(finished: JobView) {
  const sent: { method: string; path: string; body: unknown }[] = []
  let current: JobView | null = null
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
      if (path === "/api/me")
        return reply({ name: "Deniz", view: "engineering", role_locked: false, role: "engineer", setup: true })
      if (path === "/api/queue") return reply({ items: [] })
      if (path === "/api/run/suites") return reply([{ suite_id: "outcomes", folder: "suites/outcomes", cases: 3, first: false }])
      if (path === "/api/run/plan") return reply(PLAN)
      if (path === "/api/run/start") {
        current = finished
        return reply(job("running"))
      }
      if (path === "/api/run/current") return reply(current)
      return reply({ detail: "not found" }, 404)
    }),
  )
  return sent
}

beforeEach(() => window.localStorage.setItem("casebench.person", "Deniz"))
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe("run", () => {
  test("run from the workbench", async () => {
    const user = userEvent.setup()
    const sent = serve(job("finished"))
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Run" }))
    expect(await screen.findByText(/target: 3 calls/)).toBeInTheDocument()
    expect(sent.some((s) => s.path === "/api/run/start")).toBe(false)

    await user.click(screen.getByRole("button", { name: /Start the run/ }))
    expect(await screen.findByText("Finished")).toBeInTheDocument()
    expect(sent.find((s) => s.path === "/api/run/start")!.body).toEqual({ suite_id: "outcomes" })
    expect(screen.getByText("20261016T100000Z-abc")).toBeInTheDocument()
    expect(screen.getByLabelText("What the run printed")).toHaveTextContent("scored 3/3")
    expect(screen.getByRole("button", { name: /Open the report/ })).toBeInTheDocument()
  })

  test("a run that could not score says so and scores what is missing", async () => {
    const user = userEvent.setup()
    const sent = serve(job("finished", 3))
    render(<App />)
    await user.click(await screen.findByRole("button", { name: "Run" }))
    await screen.findByText(/target: 3 calls/)
    await user.click(screen.getByRole("button", { name: /Start the run/ }))
    expect(await screen.findByText("3 results could not be scored")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Score what is missing/ }))
    const starts = sent.filter((s) => s.path === "/api/run/start")
    expect(starts.at(-1)!.body).toEqual({ suite_id: "outcomes", run_id: "20261016T100000Z-abc" })
  })
})

// A suite's history in the browser (decision 0067); the API is tested in
// tests/workbench/test_run_history.py.

import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

import { App } from "@/app"
import type { History, HistoryPoint } from "@/lib/api"
import { serveApi } from "@/test-api"

const RUNS = ["n1", "n2", "n3"]
const point = (run_id: string, mean: number): HistoryPoint => ({ run_id, n: 4, mean, low: mean - 0.2, high: Math.min(1, mean + 0.2) })
const line = (means: number[]) => means.map((m, i) => point(RUNS[i], m))
const outcome = (area: string | null, means: number[]) => ({
  task_type: "qa",
  metric: "outcome",
  name: "Ruling correct",
  direction: "higher",
  reference_source: "court",
  approval: "approved",
  practice_area: area,
  points: line(means),
  moved: [],
})
const HISTORY: History = {
  suite_id: "labour",
  runs: [
    { run_id: "n1", scored_at: "2026-10-17T02:00:00Z", target: "agent", commit: "a1b2c3d4", changed: [] },
    { run_id: "n2", scored_at: "2026-10-18T02:00:00Z", target: "agent", commit: "b2c3d4e5", changed: [] },
    { run_id: "n3", scored_at: "2026-10-19T02:00:00Z", target: "agent", commit: "c3d4e5f6", changed: ["judge"] },
  ],
  series: [
    outcome(null, [0.5, 0.75, 1]),
    outcome("tax", [0.5, 0.5, 1]),
    { ...outcome(null, [0.75, 1, 1]), metric: "criteria", name: "Criteria met, weighted", moved: ["n3"] },
  ],
  rates: [{ error: "wrong outcome", meaning: "The answer states another ruling.", points: line([0.5, 0.5, 0.25]) }],
}

beforeEach(() => {
  window.localStorage.setItem("casebench.person", "Ayşe")
  serveApi({
    "/api/session": () => ({ role_locked: true }),
    "/api/me": () => ({ name: "Ayşe", view: "review", role_locked: true, role: "reviewer", setup: false }),
    "/api/queue": () => ({ items: [] }),
    "/api/history": () => [{ suite_id: "labour", runs: 3, last: "2026-10-19T02:00:00Z" }],
    "/api/history/labour": () => HISTORY,
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

test("history over time", async () => {
  const user = userEvent.setup()
  render(<App />)
  await user.click(await screen.findByRole("button", { name: "History" }))

  const ruling = await screen.findByRole("article", { name: "Ruling correct" })
  expect(within(ruling).getByLabelText("Latest: 100%")).toBeInTheDocument()
  expect(within(ruling).getByText("+25 points, better")).toBeInTheDocument()
  const rate = screen.getByRole("article", { name: "Wrong outcome" })
  expect(within(rate).getByText("-25 points, better")).toBeInTheDocument()
  // The run where the judge changed is named in the runs table.
  expect(screen.getByRole("cell", { name: "judge" })).toBeInTheDocument()

  // One practice area at a time: tax stayed at half until the third night.
  await user.click(screen.getByRole("combobox", { name: "Practice area" }))
  await user.click(await screen.findByRole("option", { name: "tax" }))
  const tax = screen.getByRole("article", { name: "Ruling correct" })
  await user.click(within(tax).getByText("Values"))
  const rows = within(tax).getAllByRole("row").slice(1).map((row) => row.textContent)
  expect(rows).toEqual(["Oct 1750%30% to 70%4", "Oct 1850%30% to 70%4", "Oct 19100%80% to 100%4"])
})

test("no history yet", async () => {
  serveApi({
    "/api/session": () => ({ role_locked: true }),
    "/api/me": () => ({ name: "Ayşe", view: "review", role_locked: true, role: "reviewer", setup: false }),
    "/api/queue": () => ({ items: [] }),
    "/api/history": () => [],
  })
  const user = userEvent.setup()
  render(<App />)
  await user.click(await screen.findByRole("button", { name: "History" }))
  expect(await screen.findByText("No history yet")).toBeInTheDocument()
})

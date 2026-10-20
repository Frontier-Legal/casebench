// A reviewer's first visit shows, once, how reviewing works (decision 0065).

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { App } from "@/app"
import { reply, serveApi } from "@/test-api"

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

test("a reviewer is shown how reviewing works once", async () => {
  const reviewer = { name: "Ayşe Yılmaz", view: "review", role_locked: true, role: "reviewer", setup: false }
  serveApi({
    "/api/session": () => ({ role_locked: true }),
    "GET /api/me": () => reply({ detail: "no one by that name yet" }, 404),
    "PUT /api/me": () => reviewer,
    "/api/queue": () => ({ items: [] }),
  })
  const user = userEvent.setup()
  const { unmount } = render(<App />)

  expect(await screen.findByRole("heading", { name: "Open the review queue" })).toBeInTheDocument()
  await user.type(screen.getByLabelText("Your name"), "Ayşe Yılmaz")
  await user.click(screen.getByRole("button", { name: "Start" }))

  expect(await screen.findByRole("heading", { name: "The evidence is beside every answer" })).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Next" }))
  expect(await screen.findByRole("heading", { name: "The judge's view is filled in" })).toBeInTheDocument()
  await user.click(screen.getByRole("button", { name: "Next" }))
  await user.click(await screen.findByRole("button", { name: "Start reviewing" }))
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

  // Opened again with the name kept, the workbench goes straight to the queue.
  unmount()
  serveApi({
    "/api/session": () => ({ role_locked: true }),
    "/api/me": () => reviewer,
    "/api/queue": () => ({ items: [] }),
  })
  render(<App />)
  expect(await screen.findByText("Nothing to review")).toBeInTheDocument()
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
})

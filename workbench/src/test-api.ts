// A stand-in workbench API for the page tests: each route answers from a function, and every
// request is recorded so a test reads what the page sent.

import { vi } from "vitest"

export type Sent = { method: string; path: string; body: unknown }
type Route = (body: unknown, method: string) => unknown

export function reply(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } })
}

/** Routes keyed by "METHOD /path" or "/path" for any method; anything else is a 404. */
export function serveApi(routes: Record<string, Route>): Sent[] {
  const sent: Sent[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = decodeURIComponent(new URL(String(input), "http://127.0.0.1").pathname)
      const method = init?.method ?? "GET"
      const body = init?.body ? JSON.parse(String(init.body)) : undefined
      sent.push({ method, path, body })
      const route = routes[`${method} ${path}`] ?? routes[path]
      if (!route) return reply({ detail: "not found" }, 404)
      const answer = route(body, method)
      return answer instanceof Response ? answer : reply(answer)
    }),
  )
  return sent
}

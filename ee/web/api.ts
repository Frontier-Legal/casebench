// SPDX-License-Identifier: Elastic-2.0
// The team server's API, as ee/casebench_ee/routes.py serves it (decision 0058).

export interface TeamStatus {
  setup_needed: boolean
  providers: { name: string; title: string }[]
  mail: boolean
}

export interface Person {
  id: number
  email: string
  name: string
  role: string
  active: boolean
  invited_by: string | null
  last_seen: string | null
  password: boolean
}

export interface Invited {
  person: Person
  emailed: boolean
  link: string | null
}

export interface KeyView {
  id: number
  name: string
  role: string
  created_by: string
  created_at: string
  revoked: boolean
}

export interface Limits {
  team: number | null
  person: number | null
}

export interface AuditEntry {
  id: number
  at: string
  by: string
  action: string
  item: string
  subject: string
  before: unknown
  after: unknown
  reason: string | null
}

export interface Targets {
  target: Record<string, unknown> | null
  agent_models: Record<string, unknown>[]
  note: string
}

export const ROLES = ["viewer", "reviewer", "editor", "engineer", "admin"] as const

export class TeamError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const parsed = (await response.json()) as { detail?: unknown }
      if (typeof parsed.detail === "string") detail = parsed.detail
    } catch {
      // Not JSON: the status text says enough.
    }
    throw new TeamError(response.status, detail)
  }
  return (await response.json()) as T
}

export const team = {
  status: () => call<TeamStatus>("GET", "/api/team/status"),
  signedIn: async () => (await fetch("/api/me", { credentials: "same-origin" })).ok,
  setup: (code: string, name: string, email: string, password: string) =>
    call<Person>("POST", "/api/team/setup", { code, name, email, password }),
  password: (email: string, password: string) =>
    call<Person>("POST", "/api/team/signin/password", { email, password }),
  link: (email: string) => call<{ message: string }>("POST", "/api/team/signin/link", { email }),
  signOut: () => call<{ signed_out: boolean }>("POST", "/api/team/signout"),
  people: () => call<Person[]>("GET", "/api/team/users"),
  invite: (email: string, name: string, role: string) =>
    call<Invited>("POST", "/api/team/users", { email, name, role }),
  newLink: (id: number) => call<Invited>("POST", `/api/team/users/${id}/link`),
  change: (id: number, change: { role?: string; active?: boolean }) =>
    call<Person>("PATCH", `/api/team/users/${id}`, change),
  keys: () => call<KeyView[]>("GET", "/api/team/keys"),
  makeKey: (name: string, role: string) =>
    call<{ key: KeyView; token: string }>("POST", "/api/team/keys", { name, role }),
  revoke: (id: number) => call<KeyView>("POST", `/api/team/keys/${id}/revoke`),
  limits: () => call<Limits>("GET", "/api/team/limits"),
  setLimits: (limits: Limits) => call<Limits>("PUT", "/api/team/limits", limits),
  targets: () => call<Targets>("GET", "/api/team/targets"),
  audit: (query: string, before?: number) =>
    call<AuditEntry[]>(
      "GET",
      `/api/team/audit?${new URLSearchParams({ query, ...(before ? { before: String(before) } : {}) })}`,
    ),
}

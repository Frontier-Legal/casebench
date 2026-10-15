// The workbench API, as casebench/workbench/app.py serves it (decision 0050).

export type Verdict = "pass" | "fail"
export type View = "review" | "engineering"
export type FactChoice = "approve" | "edit" | "reject"

export interface Session {
  role_locked: boolean
}

export interface Me {
  name: string
  view: View
  role_locked: boolean
}

export interface QueueItem {
  key: string
  kind: "answer" | "draft"
  title: string
  where: string
  task: string
  flags: string[]
}

export interface Highlight {
  start: number
  end: number
}

export interface Input {
  name: string
  text: string
}

export interface FactView {
  id: string
  kind: string
  value: string
  document: string
  quote: string | null
  note: string | null
  document_id: string | null
  highlight: Highlight | null
}

export interface LawyerView {
  verdict: Verdict
  by: string
  note: string | null
  at: string
}

export interface CriterionView {
  id: string
  text: string
  weight: number
  kind: string | null
  judge: Verdict
  judge_quote: string | null
  judge_note: string | null
  evidence: string[]
  lawyer: LawyerView | null
  judges_disagreed: boolean
}

export interface CitationView {
  citation: string
  claim: string
  label: "verified" | "misgrounded" | "fabricated" | "unchecked"
  document_id: string | null
  quote: string | null
  reason: string | null
}

export interface ScoreView {
  metric: string
  value: number
  label: string | null
}

export interface StepView {
  kind: string
  name: string | null
  model: string | null
  duration_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
}

export interface Engineering {
  latency_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
  cost: number | null
  steps: StepView[]
  raw: Record<string, unknown>
}

export interface DecisionView {
  id: string
  court: string | null
  date: string | null
  text: string | null
}

export interface Document extends DecisionView {
  highlight: Highlight | null
}

interface ItemBase {
  key: string
  title: string
  where: string
  task: string
  inputs: Input[]
  draft: Record<string, unknown> | null
  held_by: string | null
  engineering: Engineering | null
}

export interface AnswerItem extends ItemBase {
  kind: "answer"
  answer: string | null
  reference: FactView[]
  criteria: CriterionView[]
  citations: CitationView[]
  scores: ScoreView[]
}

export interface DraftItem extends ItemBase {
  kind: "draft"
  decision: DecisionView | null
  facts: FactView[]
}

export type Item = AnswerItem | DraftItem

export interface GivenVerdict {
  criterion_id: string
  verdict: Verdict
  note?: string | null
}

export interface GivenFact {
  fact_id: string
  decision: FactChoice
  value?: string | null
  reason?: string | null
}

export interface Finished {
  key: string
  message: string
}

const PERSON = "casebench.person"

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function storedName(): string | null {
  try {
    return window.localStorage.getItem(PERSON)
  } catch {
    return null
  }
}

export function storeName(name: string | null): void {
  try {
    if (name) window.localStorage.setItem(PERSON, name)
    else window.localStorage.removeItem(PERSON)
  } catch {
    // A private window keeps no storage; the name is asked again next time.
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  const name = storedName()
  if (name) headers["X-Casebench-Person"] = encodeURIComponent(name)
  if (body !== undefined) headers["Content-Type"] = "application/json"
  const response = await fetch(path, {
    method,
    headers,
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
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}

const item = (key: string) => `/api/items/${encodeURIComponent(key)}`

export const api = {
  session: () => call<Session>("GET", "/api/session"),
  me: () => call<Me>("GET", "/api/me"),
  saveMe: (name: string, view: View) => call<Me>("PUT", "/api/me", { name, view }),
  queue: () => call<{ items: QueueItem[] }>("GET", "/api/queue"),
  item: (key: string) => call<Item>("GET", item(key)),
  reserve: (key: string) => call<{ held_by: string }>("POST", `${item(key)}/reserve`),
  saveDraft: (key: string, payload: Record<string, unknown>) =>
    call<{ held_by: string }>("PUT", `${item(key)}/draft`, { payload }),
  finishAnswer: (key: string, verdicts: GivenVerdict[]) =>
    call<Finished>("POST", `${item(key)}/finish`, { verdicts }),
  finishDraft: (key: string, facts: GivenFact[]) =>
    call<Finished>("POST", `${item(key)}/finish`, { facts }),
  document: (id: string, quote?: string | null) =>
    call<Document>(
      "GET",
      `/api/documents/${encodeURIComponent(id)}${quote ? `?quote=${encodeURIComponent(quote)}` : ""}`,
    ),
}

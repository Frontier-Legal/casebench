// The workbench API, as casebench/workbench/app.py serves it (decision 0050).

export type Verdict = "pass" | "fail"
export type View = "review" | "engineering"
export type FactChoice = "approve" | "edit" | "reject"

export interface Session {
  role_locked: boolean
  /** local, or team when people sign in (decision 0058). */
  mode?: "local" | "team"
  /** An engineer's own machine with no casebench.yaml yet: the guide comes first (0065). */
  setting_up?: boolean
}

export interface Me {
  name: string
  view: View
  role_locked: boolean
  role?: string
  /** What the caller may do: read, review, compare, try, edit, engineer, admin. */
  can?: string[]
  /** An engineer at a workbench on their own machine: settings and runs are theirs (0063). */
  setup?: boolean
}

// The Settings page (decision 0063).

export interface ModelView {
  role: string
  used_for: string
  provider: string
  model: string
  family: string | null
  max_tokens: number | null
  context_window: number | null
  price_input: number | null
  price_output: number | null
  settings: Record<string, unknown>
  key: string | null
  base_url: string | null
}

export interface KeyView {
  name: string
  /** Whether a value is found, never what it is. */
  where: "shell" | "file" | "missing"
  file: string | null
  used_by: string[]
}

export interface RunSpend {
  run_id: string
  suite_id: string
  scored: boolean
  agent: number | null
  judge: number | null
  total: number | null
  unpriced: string[]
}

export interface Plugins {
  targets: string[]
  connectors: string[]
  providers: string[]
}

export type Sections = Record<string, unknown>

export interface SettingsView {
  file: string | null
  exists: boolean
  editable: boolean
  problem: string | null
  has_comments: boolean
  sections: Sections
  text: string
  models: ModelView[]
  keys: KeyView[]
  budget: Budget | null
  runs: RunSpend[]
  plugins: Plugins
}

export interface CheckView {
  part: string
  status: string
  passed: boolean
  reason: string
  next: string
}

export interface CatalogProvider {
  id: string
  name: string
  models: number
}

export interface CatalogModel {
  id: string
  name: string
  family: string | null
  price_input: number | null
  price_output: number | null
  context_window: number | null
  max_output: number | null
}

export interface Picked {
  block: Record<string, unknown> | null
  missing: string[]
  plugins: string[]
}

// The setup guide, Jurisdictions and Models pages (decision 0065).

export interface ScanView {
  said: string
  /** Functions Casebench can call with a question, as path.py:function. */
  entries: string[]
  clients: string[]
  models: string[]
}

export type Tested = CheckView

/** A model the agent's code names, with its catalog family and price (0047, 0051). */
export interface AgentModelRow {
  model: string
  family: string
  price?: { input: number; output: number } | null
}

export interface Leaf {
  path: string
  value: string
}

/** What a person has picked in a source's search result and document so far. */
export interface Picks {
  probe: string
  jurisdictions: string[]
  result_fields?: Record<string, string>
  fields?: Record<string, string>
}

export interface ApiAsked extends Picks {
  base_url: string
  search_path: string
  fetch_path: string
  query_param?: string
  key_env?: string | null
  key_header?: string
}

export interface McpReach {
  command?: string | null
  url?: string | null
}

export interface McpAsked extends McpReach, Picks {
  search_tool: string
  search_arg?: string
  fetch_tool: string
  fetch_arg?: string
}

export interface Tool {
  name: string
  description: string
}

export interface ProfileView {
  id: string
  name: string
  jurisdictions: string[]
  key_env: string | null
  key_found: boolean
  docs: string | null
  terms: string | null
}

export interface FromProfile {
  name: string
  block: Record<string, unknown>
  notes: string[]
}

export interface Connected {
  name: string
  results: string | null
  result_choices: Leaf[]
  document_choices: Leaf[]
  fields: Record<string, string>
  missing: string[]
  /** The corpus block, once a document was fetched. */
  block: Record<string, unknown> | null
}

// A suite's history, run by run (decision 0067).

export interface SuiteHistory {
  suite_id: string
  runs: number
  last: string | null
}

export interface HistoryRun {
  run_id: string
  scored_at: string | null
  target: string
  commit: string | null
  /** Settings that differ from the run before, by name. */
  changed: string[]
}

export interface HistoryPoint {
  run_id: string
  n: number
  mean: number
  low: number
  high: number
}

export interface HistorySeries {
  task_type: string
  metric: string
  name: string
  direction: "higher" | "lower" | string
  reference_source: string
  approval: string
  /** null is every practice area together. */
  practice_area: string | null
  points: HistoryPoint[]
  /** Runs whose settings moved this metric. */
  moved: string[]
}

export interface RateSeries {
  error: string
  meaning: string
  points: HistoryPoint[]
}

export interface History {
  suite_id: string
  runs: HistoryRun[]
  series: HistorySeries[]
  rates: RateSeries[]
}

// The Run page (decision 0063).

export interface SuiteChoice {
  suite_id: string
  folder: string
  cases: number
  first: boolean
}

export interface RunPlan {
  lines: string[]
  can_start: boolean
  why_not: string | null
}

export interface RunAsked {
  suite_id: string | null
  sample?: number
  cases?: number
  /** A run to resume: only what it misses is answered and scored. */
  run_id?: string | null
}

export interface JobView {
  id: string
  title: string
  suite_id: string | null
  state: "running" | "finished" | "failed" | "stopped"
  started_at: string
  finished_at: string | null
  exit_code: number | null
  run_id: string | null
  answered: number
  scored: number
  total: number | null
  /** Results the judge could not score this time. */
  unscored: number
  line_count: number
  lines: string[]
}

export interface QueueItem {
  key: string
  kind: "answer" | "draft" | "change"
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

export interface Waiting {
  id: number
  kind: "new" | "change"
  author: string
  at: string
  reason: string | null
}

export interface FieldChange {
  field: string
  before: string
  after: string
}

export interface ChangeItem {
  key: string
  kind: "change"
  title: string
  where: string
  task: string
  proposal: Waiting
  changes: FieldChange[]
  draft: Record<string, unknown> | null
  held_by: string | null
  engineering: null
}

export type Item = AnswerItem | DraftItem | ChangeItem

export interface CaseRow {
  case_id: string
  title: string
  task: string
  source: string
  approval: "approved" | "draft"
  editable: boolean
  waiting: Waiting | null
}

export interface Golden {
  suites: { suite_id: string; cases: CaseRow[] }[]
  tasks: string[]
  second_approval: boolean
}

export interface FormField {
  name: string
  value: string
  help: string
}

export interface CaseDetail {
  suite_id: string
  case_id: string
  title: string
  task: string
  source: string
  approval: "approved" | "draft"
  author: string | null
  editable: boolean
  fields: FormField[]
  waiting: Waiting | null
}

export interface Budget {
  target: string | null
  limit: number | null
  spent_today: number
  remaining: number | null
  can_ask: boolean
  why_not: string | null
  checks_citations: boolean
}

export interface Tried {
  question: string
  answer: string | null
  error: string | null
  citations: CitationView[]
  agent_cost: number | null
  judge_cost: number | null
  cost: number
  unpriced: string[]
  budget: Budget
}

export interface Proposed {
  suite_id: string
  case_id: string
  proposal: number | null
  message: string
}

export interface RunRow {
  run_id: string
  suite_id: string
  target: string
  scored: boolean
}

export interface FailingAnswer {
  key: string
  case_id: string
  repeat: number
  title: string
}

export interface RateView {
  error: string
  meaning: string
  n: number
  rate: number
  low: number
  high: number
  failing: FailingAnswer[]
}

export interface RunReport {
  run_id: string
  suite_id: string
  target: string
  rates: RateView[]
}

export type Shown = "a" | "b" | "equal"

export interface PairRow {
  case_id: string
  repeat: number
  title: string
  practice_area: string | null
  given: boolean
}

export interface AreaView {
  practice_area: string | null
  n: number
  wins: number
  losses: number
  ties: number
  mean: number
  low: number
  high: number
  sign_p: number
  significant: boolean
}

export interface Comparison {
  first: string
  second: string
  suite_id: string
  pairs: PairRow[]
  areas: AreaView[]
}

export interface Revealed {
  choice: Shown
  reason: string
  by: string
  at: string
  a_run: string
  b_run: string
}

export interface Pair {
  case_id: string
  repeat: number
  title: string
  inputs: Input[]
  reference: FactView[]
  a: string | null
  b: string | null
  given: Revealed | null
}

export interface Bar {
  number: number
  kind: string
  name: string | null
  model: string | null
  at_ms: number | null
  duration_ms: number | null
  input_tokens: number | null
  output_tokens: number | null
  cost: number | null
  arguments: string | null
  unaccounted: boolean
}

export interface Total {
  name: string
  calls: number
  input_tokens: number
  output_tokens: number
  cost: number | null
  duration_ms: number
}

export interface Authority {
  document_id: string
  retrieved: number | null
  kept: number | null
  read: number | null
  cited: boolean | null
  characterised: boolean | null
  checked: string[]
}

export interface StepDiff {
  step: string
  before_ms: number | null
  after_ms: number | null
  before_tokens: number | null
  after_tokens: number | null
  changes: string[]
}

export interface Harness {
  run_id: string
  case_id: string
  repeat: number
  latency_ms: number | null
  span_ms: number | null
  unaccounted_ms: number
  outside_ms: number
  bars: Bar[]
  untimed: number
  by_step: Total[]
  by_model: Total[]
  priced: boolean
  funnel: Authority[] | null
  funnel_possible: boolean
  against: string | null
  diff: StepDiff[]
  funnel_before: Authority[] | null
}

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

export type ExportKind = "pdf" | "docx" | "html"

/** The report for partners as a file the browser saves (decision 0054). */
export async function downloadReport(run: string, kind: ExportKind): Promise<string> {
  const headers: Record<string, string> = {}
  const name = storedName()
  if (name) headers["X-Casebench-Person"] = encodeURIComponent(name)
  const response = await fetch(`/api/runs/${encodeURIComponent(run)}/export/${kind}`, { headers })
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
  const disposition = response.headers.get("Content-Disposition") ?? ""
  const file = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `casebench-${run}.${kind}`
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement("a")
  link.href = url
  link.download = file
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return file
}

const item = (key: string) => `/api/items/${encodeURIComponent(key)}`
const pairPath = (first: string, second: string, caseId: string, repeat: number) =>
  `/api/compare/${[first, second, caseId, String(repeat)].map(encodeURIComponent).join("/")}`

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
  finishChange: (key: string, decision: "approve" | "reject", note: string | null) =>
    call<Finished>("POST", `${item(key)}/finish`, { decision, note }),
  golden: () => call<Golden>("GET", "/api/golden"),
  runs: () => call<RunRow[]>("GET", "/api/runs"),
  harness: (run: string, caseId: string, repeat: number, against: string | null) =>
    call<Harness>(
      "GET",
      `/api/harness/${[run, caseId, String(repeat)].map(encodeURIComponent).join("/")}${
        against ? `?against=${encodeURIComponent(against)}` : ""
      }`,
    ),
  comparison: (first: string, second: string) =>
    call<Comparison>("GET", `/api/compare/${encodeURIComponent(first)}/${encodeURIComponent(second)}`),
  pair: (first: string, second: string, caseId: string, repeat: number) =>
    call<Pair>("GET", pairPath(first, second, caseId, repeat)),
  prefer: (first: string, second: string, caseId: string, repeat: number, choice: Shown, reason: string) =>
    call<Pair>("POST", pairPath(first, second, caseId, repeat), { choice, reason }),
  runReport: (run: string) => call<RunReport>("GET", `/api/runs/${encodeURIComponent(run)}/report`),
  budget: () => call<Budget>("GET", "/api/try"),
  tryQuestion: (question: string) => call<Tried>("POST", "/api/try", { question }),
  goldenCase: (suite: string, id: string) =>
    call<CaseDetail>("GET", `/api/golden/${encodeURIComponent(suite)}/${encodeURIComponent(id)}`),
  blankForm: (task: string) => call<FormField[]>("GET", `/api/golden/forms/${encodeURIComponent(task)}`),
  proposeChange: (suite: string, id: string, fields: Record<string, string>, reason: string) =>
    call<Proposed>(
      "PUT",
      `/api/golden/${encodeURIComponent(suite)}/${encodeURIComponent(id)}`,
      { fields, reason },
    ),
  createCase: (suite: string, task: string, fields: Record<string, string>, reason: string | null) =>
    call<Proposed>("POST", `/api/golden/${encodeURIComponent(suite)}`, { task, fields, reason }),
  document: (id: string, quote?: string | null) =>
    call<Document>(
      "GET",
      `/api/documents/${encodeURIComponent(id)}${quote ? `?quote=${encodeURIComponent(quote)}` : ""}`,
    ),
  settings: () => call<SettingsView>("GET", "/api/settings"),
  saveSection: (section: string, value: unknown) =>
    call<SettingsView>("PUT", `/api/settings/sections/${encodeURIComponent(section)}`, { value }),
  saveFile: (text: string) => call<SettingsView>("PUT", "/api/settings/file", { text }),
  setKey: (name: string, value: string) =>
    call<SettingsView>("PUT", `/api/settings/keys/${encodeURIComponent(name)}`, { value }),
  check: () => call<CheckView[]>("POST", "/api/settings/check"),
  catalog: () => call<CatalogProvider[]>("GET", "/api/settings/catalog"),
  catalogModels: (provider: string) =>
    call<CatalogModel[]>("GET", `/api/settings/catalog/${encodeURIComponent(provider)}`),
  pickModel: (provider: string, model: string, plugin?: string | null) =>
    call<Picked>("POST", "/api/settings/catalog/model", { provider, model, plugin: plugin ?? null }),
  scan: () => call<ScanView>("GET", "/api/setup/scan"),
  agentModels: () => call<AgentModelRow[]>("GET", "/api/setup/agent-models"),
  jurisdictionCodes: () => call<string[]>("GET", "/api/setup/jurisdictions"),
  testSource: (block: Record<string, unknown>, probe?: string | null) =>
    call<Tested>("POST", "/api/setup/sources/test", { block, probe: probe ?? null }),
  connectApi: (asked: ApiAsked) => call<Connected>("POST", "/api/setup/sources/api", asked),
  mcpTools: (reach: McpReach) => call<Tool[]>("POST", "/api/setup/sources/mcp/tools", reach),
  connectMcp: (asked: McpAsked) => call<Connected>("POST", "/api/setup/sources/mcp", asked),
  profiles: () => call<ProfileView[]>("GET", "/api/setup/profiles"),
  connectProfile: (given: string, jurisdictions: string[]) =>
    call<FromProfile>("POST", "/api/setup/sources/profile", { given, jurisdictions }),
  testModel: (block: Record<string, unknown>) => call<Tested>("POST", "/api/setup/models/test", { block }),
  histories: () => call<SuiteHistory[]>("GET", "/api/history"),
  history: (suite: string) => call<History>("GET", `/api/history/${encodeURIComponent(suite)}`),
  runSuites: () => call<SuiteChoice[]>("GET", "/api/run/suites"),
  runPlan: (asked: RunAsked) => call<RunPlan>("POST", "/api/run/plan", asked),
  runStart: (asked: RunAsked) => call<JobView>("POST", "/api/run/start", asked),
  runCurrent: (since: number) => call<JobView | null>("GET", `/api/run/current?since=${since}`),
  runStop: (id: string) => call<JobView>("POST", `/api/run/${encodeURIComponent(id)}/stop`),
}

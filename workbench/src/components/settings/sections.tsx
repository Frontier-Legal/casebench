// Each part of casebench.yaml as the Settings page edits it: the agent, the corpora, the judges,
// the extraction models, the limits, the network, capture, the keys and the team server. Each
// is saved whole, and the server validates it as every command reads the file (decision 0063).

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { KeyRoundIcon, PlusIcon, Trash2Icon, Undo2Icon } from "lucide-react"

import { Section, Status } from "@/components/section"
import {
  CheckField,
  ChoiceField,
  JsonField,
  NumberField,
  OptionsField,
  PickField,
  TagsField,
  TextField,
} from "@/components/settings/fields"
import { ModelEditor, type ModelBlock } from "@/components/settings/model-editor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { api, type KeyView, type SettingsView } from "@/lib/api"

type Json = Record<string, unknown>
export type Save = (section: string, value: unknown) => Promise<boolean>

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

/** A setting as the file should hold it: what is left empty is left out. */
export function clean(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(clean)
  if (value && typeof value === "object") {
    const out: Json = {}
    for (const [key, item] of Object.entries(value)) {
      const kept = clean(item)
      if (kept === null || kept === undefined || kept === "") continue
      out[key] = kept
    }
    return out
  }
  return value
}

function same(a: unknown, b: unknown): boolean {
  return JSON.stringify(clean(a)) === JSON.stringify(clean(b))
}

/** A card that edits one section: its draft, and the buttons that save, undo or remove it. */
function SectionCard<T>({
  title,
  description,
  name,
  value,
  empty,
  save,
  removeLabel,
  children,
  id,
}: {
  title: string
  description: React.ReactNode
  name: string
  value: T | undefined | null
  empty: T
  save: Save
  removeLabel?: string
  children: (draft: T, set: (draft: T) => void) => React.ReactNode
  id?: string
}) {
  const start = value ?? empty
  const [draft, setDraft] = useState<T>(start)
  const [busy, setBusy] = useState(false)
  const saved = JSON.stringify(value ?? null)
  // The draft starts again from what was saved, whenever that changes.
  useEffect(() => setDraft((value ?? empty) as T), [saved])
  const dirty = !same(draft, start)

  async function store(next: unknown) {
    setBusy(true)
    try {
      if (await save(name, next)) toast.success(`${title} saved to casebench.yaml`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      id={id}
      title={title}
      description={description}
      footer={
        <div className="flex w-full flex-wrap items-center gap-2">
          <Button onClick={() => store(clean(draft))} disabled={!dirty || busy}>
            {busy && <Spinner />} Save
          </Button>
          <Button variant="ghost" onClick={() => setDraft(start)} disabled={!dirty || busy}>
            <Undo2Icon /> Undo changes
          </Button>
          {removeLabel && value != null && (
            <Button
              variant="ghost"
              className="ml-auto text-destructive hover:text-destructive"
              onClick={() => store(null)}
              disabled={busy}
            >
              <Trash2Icon /> {removeLabel}
            </Button>
          )}
          {dirty && <span className="text-xs text-muted-foreground">Unsaved changes</span>}
        </div>
      }
    >
      <div className="flex flex-col gap-5">{children(draft, setDraft)}</div>
    </Section>
  )
}

// The agent.

const TARGET_HELP: Record<string, string> = {
  python: "A function in this project, run in worker processes as the project runs it.",
  http: "An endpoint the agent already serves, or one Casebench starts with a command.",
  command: "A program run once per case; its standard output is the answer.",
}

function TargetFields({
  target,
  set,
}: {
  target: Json
  set: (target: Json) => void
}) {
  const type = String(target.type ?? "")
  const field = (name: string) => target[name] as string | null | undefined
  const number = (name: string) => target[name] as number | null | undefined
  if (type === "python") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Function"
          className="sm:col-span-2"
          description="A file and the function in it, as path/to/agent.py:answer, or a module, as package.agent:answer. A path is relative to casebench.yaml."
          value={field("entry")}
          onChange={(entry) => set({ ...target, entry })}
        />
        <NumberField
          label="Cases at once"
          step="1"
          min={1}
          value={number("max_concurrency") ?? 1}
          onChange={(max_concurrency) => set({ ...target, max_concurrency })}
        />
      </div>
    )
  }
  if (type === "http") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="URL"
          type="url"
          className="sm:col-span-2"
          description="Where each case is sent. ${NAME} reads a variable."
          value={field("url")}
          onChange={(url) => set({ ...target, url })}
        />
        <ChoiceField
          label="Method"
          value={field("method") ?? "POST"}
          choices={["POST", "PUT", "GET"].map((m) => ({ value: m, label: m }))}
          onChange={(method) => set({ ...target, method })}
        />
        <NumberField
          label="Cases at once"
          step="1"
          min={1}
          value={number("max_concurrency") ?? 1}
          onChange={(max_concurrency) => set({ ...target, max_concurrency })}
        />
        <TextField
          label="Answer"
          description="The JSONPath to the answer in the response, such as $.answer."
          value={field("answer")}
          onChange={(answer) => set({ ...target, answer })}
        />
        <TextField
          label="Citations"
          description="The JSONPath to the citations, when the response lists them."
          value={field("citations")}
          onChange={(citations) => set({ ...target, citations })}
        />
        <TextField
          label="Documents"
          description="The JSONPath to the documents the agent read, when the response lists them."
          value={field("documents")}
          onChange={(documents) => set({ ...target, documents })}
        />
        <NumberField
          label="Timeout (seconds)"
          value={number("timeout_s")}
          min={0}
          onChange={(timeout_s) => set({ ...target, timeout_s })}
        />
        <TextField
          label="Start command"
          className="sm:col-span-2"
          description="Casebench starts the agent with this before the run, and stops it after; leave it empty for an agent that is already running."
          value={field("start")}
          onChange={(start) => set({ ...target, start })}
        />
        <OptionsField
          label="Headers"
          noun="header"
          className="sm:col-span-2"
          description="Sent with each case. Name a key as ${NAME}; never write one here."
          value={(target.headers as Json) ?? {}}
          onChange={(headers) => set({ ...target, headers })}
        />
        <JsonField
          key={`body-${type}`}
          label="Body"
          className="sm:col-span-2"
          description="The request body, as JSON; {question} and the case's other inputs are filled in."
          value={target.body ?? { question: "{question}" }}
          onChange={(body) => set({ ...target, body })}
        />
      </div>
    )
  }
  if (type === "command") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Command"
          className="sm:col-span-2"
          description="Run once per case; {question} and the case's other inputs are filled in."
          value={field("run")}
          onChange={(run) => set({ ...target, run })}
        />
        <NumberField
          label="Cases at once"
          step="1"
          min={1}
          value={number("max_concurrency") ?? 1}
          onChange={(max_concurrency) => set({ ...target, max_concurrency })}
        />
      </div>
    )
  }
  return (
    <JsonField
      key={`other-${type}`}
      label="The target's settings"
      description="This target comes from a plugin; its settings are the plugin's."
      value={target}
      onChange={(value) => set((value as Json) ?? { type })}
    />
  )
}

export function AgentSections({ view, save }: { view: SettingsView; save: Save }) {
  const targets = Array.from(new Set(["python", "http", "command", ...view.plugins.targets]))
  type Row = { model?: string; family?: string; price?: { input?: number | null; output?: number | null } | null }
  return (
    <>
      <SectionCard<Json>
        title="The agent"
        name="target"
        description="How Casebench sends each case to the AI it measures."
        value={view.sections.target as Json | undefined}
        empty={{ type: "python" }}
        save={save}
        removeLabel="Remove the agent"
      >
        {(target, set) => (
          <>
            <ChoiceField
              label="How it is called"
              description={TARGET_HELP[String(target.type)]}
              value={String(target.type ?? "")}
              choices={targets.map((t) => ({ value: t, label: t }))}
              onChange={(type) => set({ type })}
            />
            <TargetFields target={target} set={set} />
          </>
        )}
      </SectionCard>
      <SectionCard<Row[]>
        title="The agent's models"
        name="agent_models"
        description="Each model the agent calls, with its family and price, so a run says what the agent spent and warns when a judge shares its family."
        value={view.sections.agent_models as Row[] | undefined}
        empty={[]}
        save={save}
      >
        {(rows, set) => (
          <>
            {rows.map((row, index) => (
              <div key={index} className="grid items-end gap-3 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
                <TextField
                  label="Model"
                  value={row.model}
                  onChange={(model) => set(rows.map((r, i) => (i === index ? { ...r, model: model ?? undefined } : r)))}
                />
                <TextField
                  label="Family"
                  value={row.family}
                  onChange={(family) => set(rows.map((r, i) => (i === index ? { ...r, family: family ?? undefined } : r)))}
                />
                <NumberField
                  label="Input $ / M"
                  value={row.price?.input}
                  min={0}
                  onChange={(input) =>
                    set(rows.map((r, i) => (i === index ? { ...r, price: { ...r.price, input } } : r)))
                  }
                />
                <NumberField
                  label="Output $ / M"
                  value={row.price?.output}
                  min={0}
                  onChange={(output) =>
                    set(rows.map((r, i) => (i === index ? { ...r, price: { ...r.price, output } } : r)))
                  }
                />
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${row.model ?? "this model"}`}
                  onClick={() => set(rows.filter((_, i) => i !== index))}
                >
                  <Trash2Icon />
                </Button>
              </div>
            ))}
            <div>
              <Button variant="outline" size="sm" onClick={() => set([...rows, {}])}>
                <PlusIcon /> Add a model
              </Button>
            </div>
          </>
        )}
      </SectionCard>
    </>
  )
}

// The corpora.

type CorpusRow = { name: string; corpus: Json }

function CorpusFields({
  row,
  set,
  connectors,
}: {
  row: CorpusRow
  set: (row: CorpusRow) => void
  connectors: string[]
}) {
  const corpus = row.corpus
  const put = (patch: Json) => set({ ...row, corpus: { ...corpus, ...patch } })
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <TextField
        label="Name"
        description="Lowercase words joined by hyphens; `corpus` when there is one."
        value={row.name}
        onChange={(name) => set({ ...row, name: name ?? "" })}
      />
      <ChoiceField
        label="Connector"
        description="How documents are read: a folder, an HTTP API, or a plugin."
        value={corpus.connector as string | undefined}
        choices={connectors.map((c) => ({ value: c, label: c }))}
        onChange={(connector) => put({ connector })}
      />
      <TagsField
        label="Jurisdictions"
        description="The codes it covers, such as TR; every one when empty."
        values={(corpus.jurisdictions as string[]) ?? []}
        onChange={(jurisdictions) => put({ jurisdictions })}
      />
      <PickField
        label="Holds"
        description="Both when none is ticked."
        options={[
          { value: "decisions", label: "Decisions" },
          { value: "statutes", label: "Statutes" },
        ]}
        values={(corpus.holds as string[]) ?? []}
        onChange={(holds) => put({ holds })}
      />
      <ChoiceField
        label="The provider charges for"
        value={(corpus.metered as string) ?? "none"}
        choices={[
          { value: "none", label: "Nothing" },
          { value: "search", label: "Each search" },
          { value: "fetch", label: "Each document" },
        ]}
        onChange={(metered) => put({ metered })}
      />
      <PickField
        label="Kept on disk"
        description="What the provider's terms let Casebench keep; when none is ticked, documents are kept, and searches when metered."
        options={[
          { value: "documents", label: "Documents" },
          { value: "searches", label: "Searches" },
        ]}
        values={(corpus.keep as string[]) ?? []}
        onChange={(keep) => put({ keep: keep.length ? keep : null })}
      />
      <TextField
        label="Probe search"
        description="The search casebench check runs to see the store answer."
        value={corpus.probe as string | undefined}
        onChange={(probe) => put({ probe })}
      />
      <TextField
        label="Link"
        description="Where a person reads a document on the provider's site, with {id} for its id."
        value={corpus.link as string | undefined}
        onChange={(link) => put({ link })}
      />
      <OptionsField
        label="Options"
        className="sm:col-span-2"
        description="The connector's: a folder's path, or an API's base_url, paths, fields and headers. Name a key as ${NAME}."
        value={(corpus.options as Json) ?? {}}
        suggestions={["path", "base_url", "headers"]}
        onChange={(options) => put({ options })}
      />
      <JsonField
        label="Search filters"
        className="sm:col-span-2"
        rows={4}
        description="What a search for each kind of citation adds, keyed by statute and decision."
        value={corpus.search_filters ?? {}}
        onChange={(search_filters) => put({ search_filters })}
      />
    </div>
  )
}

export function CorpusSection({ view, save }: { view: SettingsView; save: Save }) {
  const corpora = (view.sections.corpora as Record<string, Json> | undefined) ?? {}
  const rows: CorpusRow[] = Object.entries(corpora).map(([name, corpus]) => ({ name, corpus }))
  const asMap = (list: CorpusRow[]) => Object.fromEntries(list.map((r) => [r.name, r.corpus]))
  return (
    <SectionCard<CorpusRow[]>
      title="Court decisions and statutes"
      name="corpora"
      description="Where Casebench reads the documents an answer cites, to check what each says."
      value={rows.length ? rows : undefined}
      empty={[]}
      save={(section, value) => save(section, value === null ? null : asMap(value as CorpusRow[]))}
      removeLabel="Remove every corpus"
    >
      {(list, set) => (
        <>
          {list.map((row, index) => (
            <div key={index} className="flex flex-col gap-4 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{row.name || "New corpus"}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => set(list.filter((_, i) => i !== index))}
                  aria-label={`Remove corpus ${row.name}`}
                >
                  <Trash2Icon /> Remove
                </Button>
              </div>
              <CorpusFields
                row={row}
                connectors={view.plugins.connectors}
                set={(next) => set(list.map((r, i) => (i === index ? next : r)))}
              />
            </div>
          ))}
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                set([...list, { name: list.length ? `corpus-${list.length + 1}` : "corpus", corpus: { connector: "folder" } }])
              }
            >
              <PlusIcon /> Add a corpus
            </Button>
          </div>
        </>
      )}
    </SectionCard>
  )
}

// The models Casebench calls itself.

export function JudgesSection({ view, save }: { view: SettingsView; save: Save }) {
  return (
    <SectionCard<ModelBlock[]>
      title="The judge"
      name="judges"
      description="The model that checks each answer's citations against the corpus and grades criteria. A second judge from another model family judges every answer again, so disagreements show."
      value={view.sections.judges as ModelBlock[] | undefined}
      empty={[{}]}
      save={save}
      removeLabel="Remove the judges"
    >
      {(judges, set) => (
        <>
          {judges.map((judge, index) => (
            <div key={index} className="flex flex-col gap-4 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{index === 0 ? "Judge" : "Second judge"}</span>
                {index > 0 && (
                  <Button variant="ghost" size="sm" onClick={() => set(judges.slice(0, 1))}>
                    <Trash2Icon /> Remove
                  </Button>
                )}
              </div>
              <ModelEditor
                judge
                block={judge}
                providers={view.plugins.providers}
                onChange={(block) => set(judges.map((j, i) => (i === index ? block : j)))}
              />
            </div>
          ))}
          {judges.length < 2 && (
            <div>
              <Button variant="outline" size="sm" onClick={() => set([...judges, {}])}>
                <PlusIcon /> Add a second judge
              </Button>
            </div>
          )}
        </>
      )}
    </SectionCard>
  )
}

export function ExtractSection({ view, save }: { view: SettingsView; save: Save }) {
  type Extract = { models: ModelBlock[] }
  return (
    <SectionCard<Extract>
      title="Extraction models"
      name="extract"
      description="Two models, not the same one twice, read court decisions and write answer keys; what both agree on becomes a case."
      value={view.sections.extract as Extract | undefined}
      empty={{ models: [{}, {}] }}
      save={save}
      removeLabel="Remove extraction"
    >
      {(extract, set) =>
        [0, 1].map((index) => (
          <div key={index} className="flex flex-col gap-4 rounded-lg border p-4">
            <span className="text-sm font-medium">Extraction model {index + 1}</span>
            <ModelEditor
              judge={false}
              block={extract.models?.[index] ?? {}}
              providers={view.plugins.providers}
              onChange={(block) =>
                set({ models: [0, 1].map((i) => (i === index ? block : (extract.models?.[i] ?? {}))) })
              }
            />
          </div>
        ))
      }
    </SectionCard>
  )
}

// Limits, the network and capture.

export function LimitsSection({ view, save }: { view: SettingsView; save: Save }) {
  type Workbench = { try_daily_limit_usd?: number | null; second_approval?: boolean }
  return (
    <SectionCard<Workbench>
      title="Limits"
      name="workbench"
      description="What trying a question in the workbench may spend each day, and how golden data changes."
      value={view.sections.workbench as Workbench | undefined}
      empty={{}}
      save={save}
    >
      {(limits, set) => (
        <>
          <NumberField
            label="Daily limit for trying questions (USD)"
            description="The agent's and the judge's calls together. With no limit, nothing is sent."
            value={limits.try_daily_limit_usd}
            min={0}
            className="max-w-sm"
            onChange={(try_daily_limit_usd) => set({ ...limits, try_daily_limit_usd })}
          />
          <CheckField
            label="A change to golden data waits for a second editor"
            description="The editor who changes a case cannot approve it."
            checked={limits.second_approval ?? false}
            onChange={(second_approval) => set({ ...limits, second_approval })}
          />
        </>
      )}
    </SectionCard>
  )
}

export function NetworkSections({ view, save }: { view: SettingsView; save: Save }) {
  type Network = { allow?: string[] }
  type Capture = { port?: number | null; traces?: boolean; routes?: unknown[]; functions?: unknown[] }
  return (
    <>
      <SectionCard<Network>
        title="Network"
        name="network"
        description="A run may call only the hosts the settings name: the agent's, the judges', the corpora's and the team server's. Add any other host the agent needs."
        value={view.sections.network as Network | undefined}
        empty={{ allow: [] }}
        save={save}
      >
        {(network, set) => (
          <TagsField
            label="Also allowed"
            placeholder="api.example.com"
            values={network.allow ?? []}
            onChange={(allow) => set({ allow })}
          />
        )}
      </SectionCard>
      <SectionCard<Capture>
        title="Capture"
        name="capture"
        description="How Casebench records the calls the agent makes during a run, so a report can say where an authority was lost."
        value={view.sections.capture as Capture | undefined}
        empty={{}}
        save={save}
        removeLabel="Remove capture settings"
      >
        {(capture, set) => (
          <>
            <NumberField
              label="Port"
              description="0 lets the system choose; name one for an agent that is already running."
              step="1"
              min={0}
              className="max-w-sm"
              value={capture.port ?? 0}
              onChange={(port) => set({ ...capture, port })}
            />
            <CheckField
              label="Point the OpenTelemetry exporter of agents Casebench starts at the recorder"
              checked={capture.traces ?? false}
              onChange={(traces) => set({ ...capture, traces })}
            />
            <JsonField
              label="Routes"
              description="Backends the recorder stands in front of: each a name, upstream, variable and parser."
              value={capture.routes ?? []}
              onChange={(routes) => set({ ...capture, routes: (routes as unknown[]) ?? [] })}
            />
            <JsonField
              label="Functions"
              description="Functions in the agent recorded as steps, such as a reranker."
              rows={4}
              value={capture.functions ?? []}
              onChange={(functions) => set({ ...capture, functions: (functions as unknown[]) ?? [] })}
            />
          </>
        )}
      </SectionCard>
    </>
  )
}

// Keys and the team server.

const WHERE: Record<KeyView["where"], { tone: "good" | "bad" | "none"; label: string }> = {
  shell: { tone: "good", label: "Set in the shell" },
  file: { tone: "good", label: "Read from a file" },
  missing: { tone: "bad", label: "Not set" },
}

export function SetKey({
  name,
  onSet,
  label = "Set",
}: {
  name: string
  onSet: (view: SettingsView) => void
  label?: string
}) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState("")
  const [busy, setBusy] = useState(false)
  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <KeyRoundIcon /> {label}
      </Button>
    )
  }
  async function submit() {
    setBusy(true)
    try {
      onSet(await api.setKey(name, value))
      toast.success(`${name} saved; it is never shown again`)
      setValue("")
      setOpen(false)
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <Input
        type="password"
        autoComplete="off"
        aria-label={`Value of ${name}`}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        className="h-8 w-56"
        autoFocus
      />
      <Button size="sm" type="submit" aria-label="Save the key" disabled={!value.trim() || busy}>
        {busy && <Spinner />} Save
      </Button>
      <Button size="sm" variant="ghost" type="button" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </form>
  )
}

export function KeysSection({
  view,
  save,
  onView,
}: {
  view: SettingsView
  save: Save
  onView: (view: SettingsView) => void
}) {
  const [name, setName] = useState("")
  return (
    <>
      <Section
        title="Keys"
        description="Each key the settings use, and whether this machine has it. A value is never shown; one typed here goes to a .env file git ignores, and Casebench uses it at once."
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Variable</TableHead>
              <TableHead>Used by</TableHead>
              <TableHead>Here</TableHead>
              <TableHead className="text-right">Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {view.keys.map((key) => (
              <TableRow key={key.name}>
                <TableCell className="font-mono text-xs">{key.name}</TableCell>
                <TableCell className="text-xs">{key.used_by.join(", ") || "–"}</TableCell>
                <TableCell>
                  <Status tone={WHERE[key.where].tone}>
                    {WHERE[key.where].label}
                    {key.file ? ` · ${key.file}` : ""}
                  </Status>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end">
                    <SetKey name={key.name} onSet={onView} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Input
            aria-label="Another key's variable name"
            placeholder="ANOTHER_API_KEY"
            className="h-8 max-w-64 font-mono text-xs"
            value={name}
            onChange={(event) => setName(event.target.value.toUpperCase())}
          />
          {name.trim() && (
            <SetKey
              name={name.trim()}
              onSet={(next) => {
                setName("")
                onView(next)
              }}
            />
          )}
        </div>
        {view.keys.some((k) => k.where === "shell") && (
          <p className="mt-3 text-xs text-muted-foreground">
            A key set in the shell is used before one in a file.
          </p>
        )}
      </Section>
      <SectionCard<Record<string, string>>
        title="Where keys are read from"
        name="keys"
        description="Each variable and the .env file it is read from, relative to casebench.yaml, when the shell does not set it."
        value={view.sections.keys as Record<string, string> | undefined}
        empty={{}}
        save={save}
      >
        {(files, set) => (
          <OptionsField
            label="Variables"
            noun="variable"
            value={files}
            onChange={(value) => set(value as Record<string, string>)}
          />
        )}
      </SectionCard>
    </>
  )
}

export function TeamServerSection({ view, save }: { view: SettingsView; save: Save }) {
  type Cloud = { url?: string; key_env?: string }
  return (
    <SectionCard<Cloud>
      title="Team server"
      name="cloud"
      description="Where lawyers review: casebench push sends runs there, and casebench pull brings their approvals and verdicts back. The laptop needs only casebench; the server runs casebench-ee."
      value={view.sections.cloud as Cloud | undefined}
      empty={{ key_env: "CASEBENCH_CLOUD_KEY" }}
      save={save}
      removeLabel="Disconnect"
    >
      {(cloud, set) => {
        const key = view.keys.find((k) => k.name === (cloud.key_env || "CASEBENCH_CLOUD_KEY"))
        return (
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Address"
              type="url"
              placeholder="https://casebench.firm.example"
              value={cloud.url}
              onChange={(url) => set({ ...cloud, url: url ?? undefined })}
            />
            <TextField
              label="Key variable"
              description={
                <>
                  An admin makes an engineer key on the server's Team page.{" "}
                  {key && <Badge variant="outline">{WHERE[key.where].label}</Badge>}
                </>
              }
              value={cloud.key_env ?? "CASEBENCH_CLOUD_KEY"}
              onChange={(key_env) => set({ ...cloud, key_env: key_env ?? undefined })}
            />
          </div>
        )
      }}
    </SectionCard>
  )
}

export function FileSection({ view, onView }: { view: SettingsView; onView: (view: SettingsView) => void }) {
  const [text, setText] = useState(view.text)
  const [busy, setBusy] = useState(false)
  useEffect(() => setText(view.text), [view.text])
  async function store() {
    setBusy(true)
    try {
      onView(await api.saveFile(text))
      toast.success("casebench.yaml saved")
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Section
      title="casebench.yaml"
      description="The whole file, as written. Saved as it is, comments included, once it validates."
      footer={
        <div className="flex gap-2">
          <Button onClick={store} disabled={busy || text === view.text}>
            {busy && <Spinner />} Save the file
          </Button>
          <Button variant="ghost" onClick={() => setText(view.text)} disabled={busy || text === view.text}>
            <Undo2Icon /> Undo changes
          </Button>
        </div>
      }
    >
      <label htmlFor="settings-file" className="sr-only">
        casebench.yaml
      </label>
      <Textarea
        id="settings-file"
        value={text}
        spellCheck={false}
        onChange={(event) => setText(event.target.value)}
        className="min-h-[28rem] font-mono text-xs leading-relaxed"
      />
    </Section>
  )
}

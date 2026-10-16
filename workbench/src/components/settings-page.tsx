// The Settings page: what each part of the setup is for and costs, and every setting in
// casebench.yaml to change, on the engineer's own machine (decision 0063).

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { CircleAlertIcon, FileCogIcon, PlayIcon, StethoscopeIcon } from "lucide-react"

import { Section, Status, Tile } from "@/components/section"
import {
  AgentSections,
  CorpusSection,
  ExtractSection,
  FileSection,
  JudgesSection,
  KeysSection,
  LimitsSection,
  NetworkSections,
  TeamServerSection,
  type Save,
} from "@/components/settings/sections"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, type CheckView, type KeyView, type SettingsView } from "@/lib/api"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function dollars(value: number | null | undefined): string {
  if (value == null) return "–"
  return value >= 0.01 || value === 0 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`
}

function perMillion(input: number | null, output: number | null): string {
  if (input == null && output == null) return "no price"
  return `$${input ?? "?"} / $${output ?? "?"} per M tokens`
}

const TABS = [
  ["overview", "Overview"],
  ["agent", "Agent"],
  ["corpus", "Corpus"],
  ["judge", "Judge"],
  ["extraction", "Extraction"],
  ["limits", "Limits"],
  ["network", "Network"],
  ["keys", "Keys"],
  ["team", "Team server"],
  ["file", "File"],
] as const

type Tab = (typeof TABS)[number][0]

function keyStatus(keys: KeyView[], name: string | null) {
  const key = keys.find((k) => k.name === name)
  if (!name) return <span className="text-muted-foreground">–</span>
  if (!key || key.where === "missing") return <Status tone="bad">{name} not set</Status>
  return <Status tone="good">{name}</Status>
}

function describeTarget(target: Record<string, unknown> | undefined): string {
  if (!target) return "Not set"
  if (target.type === "python") return `Python function ${target.entry ?? "?"}`
  if (target.type === "http") return `HTTP ${target.method ?? "POST"} ${target.url ?? "?"}`
  if (target.type === "command") return `Command ${target.run ?? "?"}`
  return `${String(target.type)} target`
}

function Overview({
  view,
  onTab,
  onRun,
}: {
  view: SettingsView
  onTab: (tab: Tab) => void
  onRun: () => void
}) {
  const [checks, setChecks] = useState<CheckView[] | null>(null)
  const [checking, setChecking] = useState(false)
  const target = view.sections.target as Record<string, unknown> | undefined
  const agentModels = (view.sections.agent_models as { model: string; family: string; price?: { input: number; output: number } }[]) ?? []
  const corpora = Object.entries((view.sections.corpora as Record<string, Record<string, unknown>>) ?? {})
  const budget = view.budget

  async function check() {
    setChecking(true)
    setChecks(null)
    try {
      setChecks(await api.check())
    } catch (error) {
      toast.error(message(error))
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Section title="What is used for what" description="Each part Casebench calls, what it does, what it costs and the key it reads.">
        <Table aria-label="What is used for what">
          <TableHeader>
            <TableRow>
              <TableHead>Part</TableHead>
              <TableHead>Used for</TableHead>
              <TableHead>Which</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Key</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow className="cursor-pointer" onClick={() => onTab("agent")}>
              <TableCell className="font-medium">Agent</TableCell>
              <TableCell className="max-w-72 text-xs whitespace-normal text-muted-foreground">
                The AI being measured: it answers each case.
              </TableCell>
              <TableCell className="max-w-80 font-mono text-xs whitespace-normal">{describeTarget(target)}</TableCell>
              <TableCell className="text-xs">–</TableCell>
              <TableCell className="text-xs">–</TableCell>
            </TableRow>
            {agentModels.map((model) => (
              <TableRow key={`agent-${model.model}`} className="cursor-pointer" onClick={() => onTab("agent")}>
                <TableCell className="pl-6 text-muted-foreground">Agent's model</TableCell>
                <TableCell className="text-xs text-muted-foreground">Called by the agent; priced so a run says what it spent.</TableCell>
                <TableCell className="font-mono text-xs">
                  {model.model} <Badge variant="outline">{model.family}</Badge>
                </TableCell>
                <TableCell className="text-xs tabular-nums">
                  {perMillion(model.price?.input ?? null, model.price?.output ?? null)}
                </TableCell>
                <TableCell className="text-xs">–</TableCell>
              </TableRow>
            ))}
            {corpora.map(([name, corpus]) => (
              <TableRow key={`corpus-${name}`} className="cursor-pointer" onClick={() => onTab("corpus")}>
                <TableCell className="font-medium">Corpus {corpora.length > 1 ? name : ""}</TableCell>
                <TableCell className="max-w-72 text-xs whitespace-normal text-muted-foreground">
                  Court decisions and statutes each citation is checked against.
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {String(corpus.connector)}
                  {Array.isArray(corpus.jurisdictions) && corpus.jurisdictions.length > 0
                    ? ` · ${corpus.jurisdictions.join(", ")}`
                    : ""}
                </TableCell>
                <TableCell className="text-xs">
                  {corpus.metered && corpus.metered !== "none" ? `charged per ${String(corpus.metered)}` : "–"}
                </TableCell>
                <TableCell className="text-xs">–</TableCell>
              </TableRow>
            ))}
            {view.models.map((model) => (
              <TableRow
                key={model.role}
                className="cursor-pointer"
                onClick={() => onTab(model.role.startsWith("extraction") ? "extraction" : "judge")}
              >
                <TableCell className="font-medium capitalize">{model.role}</TableCell>
                <TableCell className="max-w-72 text-xs whitespace-normal text-muted-foreground">{model.used_for}</TableCell>
                <TableCell className="font-mono text-xs whitespace-normal">
                  {model.provider} · {model.model}
                  {model.family && <Badge variant="outline" className="ml-1">{model.family}</Badge>}
                  <div className="mt-0.5 font-sans text-muted-foreground">
                    {[
                      model.max_tokens ? `up to ${model.max_tokens} output tokens` : null,
                      model.context_window ? `${model.context_window.toLocaleString()} token window` : null,
                      ...Object.entries(model.settings)
                        .filter(([name]) => name !== "max_tokens")
                        .map(([name, value]) => `${name.replace("_", " ")} ${String(value)}`),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </TableCell>
                <TableCell className="text-xs tabular-nums">{perMillion(model.price_input, model.price_output)}</TableCell>
                <TableCell className="text-xs">{keyStatus(view.keys, model.key)}</TableCell>
              </TableRow>
            ))}
            {!target && view.models.length === 0 && corpora.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                  Nothing is set up yet. Start with the agent.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Section>

      <Section
        title="Spend"
        description="What trying questions spent today, and what each recent run cost."
        action={
          <Button variant="outline" size="sm" onClick={() => onTab("limits")}>
            Change limits
          </Button>
        }
      >
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Tile label="Daily limit, trying questions" value={dollars(budget?.limit)} caption={budget?.limit == null ? "None set: nothing is sent" : "The agent and the judge together"} />
          <Tile label="Spent today" value={dollars(budget?.spent_today ?? 0)} caption="Resets at midnight UTC" />
          <Tile
            label="Left today"
            value={dollars(budget?.remaining)}
            caption={budget?.can_ask ? "Trying questions is open" : "Trying questions is closed: see Try a question"}
          />
        </div>
        {view.runs.length > 0 && (
          <Table className="mt-4">
            <TableHeader>
              <TableRow>
                <TableHead>Run</TableHead>
                <TableHead>Suite</TableHead>
                <TableHead className="text-right">Agent</TableHead>
                <TableHead className="text-right">Judge</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {view.runs.map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell className="max-w-56 truncate font-mono text-xs">{run.run_id}</TableCell>
                  <TableCell className="text-xs">{run.suite_id}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">{run.scored ? dollars(run.agent) : "not scored"}</TableCell>
                  <TableCell className="text-right text-xs tabular-nums">{run.scored ? dollars(run.judge) : "–"}</TableCell>
                  <TableCell className="text-right text-xs font-medium tabular-nums">
                    {run.scored ? dollars(run.total) : "–"}
                    {run.unpriced.length > 0 && (
                      <span className="block font-normal text-muted-foreground">without {run.unpriced.join(", ")}</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      <Section
        title="Check the setup"
        description="Calls the agent, the judge and the corpus once each, as casebench check does, and says what to fix."
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onRun}>
              <PlayIcon /> Run
            </Button>
            <Button size="sm" onClick={check} disabled={checking || !view.exists}>
              {checking ? <Spinner /> : <StethoscopeIcon />} Check
            </Button>
          </div>
        }
      >
        {checks === null ? (
          <p className="text-sm text-muted-foreground">
            {checking ? "Checking. A check waits for each part to answer." : "Not checked yet in this session."}
          </p>
        ) : (
          <ul aria-label="Checks" className="flex flex-col divide-y">
            {checks.map((item) => (
              <li key={item.part} className="flex flex-col gap-1 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="w-28 shrink-0 text-sm font-medium">{item.part}</span>
                  <Status tone={item.passed ? "good" : item.status === "failed" ? "bad" : "warn"}>{item.status}</Status>
                </div>
                {item.reason && <p className="pl-31 text-xs text-muted-foreground">{item.reason}</p>}
                {item.next && <p className="pl-31 text-xs">Next: {item.next}</p>}
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

export function SettingsPage({ onRun }: { onRun: () => void }) {
  const [view, setView] = useState<SettingsView | null>(null)
  const [tab, setTab] = useState<Tab>("overview")
  const [asking, setAsking] = useState(false)
  const answer = useRef<((go: boolean) => void) | null>(null)
  const acceptedDrop = useRef(false)

  const load = useCallback(async () => setView(await api.settings()), [])
  useEffect(() => {
    load().catch((error) => toast.error(message(error)))
  }, [load])

  // Saving a section rewrites the file, which drops comments other than its header (0042).
  function mayDropComments(): Promise<boolean> {
    if (!view?.has_comments || acceptedDrop.current) return Promise.resolve(true)
    setAsking(true)
    return new Promise((resolve) => {
      answer.current = (go) => {
        acceptedDrop.current = go
        setAsking(false)
        resolve(go)
      }
    })
  }

  const save: Save = async (section, value) => {
    if (!(await mayDropComments())) return false
    try {
      setView(await api.saveSection(section, value))
      return true
    } catch (error) {
      toast.error(message(error))
      return false
    }
  }

  if (!view) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-10" />
        <Skeleton className="h-72" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Settings</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          What Casebench calls, what each part is for and what it may spend. Every change is saved to{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">{view.file ?? "casebench.yaml"}</code>, which the
          command line and CI read too.
        </p>
      </div>
      {!view.exists && (
        <Alert>
          <FileCogIcon />
          <AlertTitle>No casebench.yaml yet</AlertTitle>
          <AlertDescription>
            The first section saved here creates it. In a terminal, casebench init finds the agent and the models
            it calls for you.
          </AlertDescription>
        </Alert>
      )}
      {view.problem && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>casebench.yaml does not validate</AlertTitle>
          <AlertDescription>
            {view.problem}. Fix it in the File tab; until then, commands that read it stop.
          </AlertDescription>
        </Alert>
      )}
      <Tabs value={tab} onValueChange={(value) => setTab(value as Tab)} className="gap-6">
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <TabsList aria-label="Settings sections">
            {TABS.map(([value, label]) => (
              <TabsTrigger key={value} value={value}>
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <TabsContent value="overview">
          <Overview view={view} onTab={setTab} onRun={onRun} />
        </TabsContent>
        <TabsContent value="agent" className="flex flex-col gap-6">
          <AgentSections view={view} save={save} />
        </TabsContent>
        <TabsContent value="corpus">
          <CorpusSection view={view} save={save} />
        </TabsContent>
        <TabsContent value="judge">
          <JudgesSection view={view} save={save} />
        </TabsContent>
        <TabsContent value="extraction">
          <ExtractSection view={view} save={save} />
        </TabsContent>
        <TabsContent value="limits">
          <LimitsSection view={view} save={save} />
        </TabsContent>
        <TabsContent value="network" className="flex flex-col gap-6">
          <NetworkSections view={view} save={save} />
        </TabsContent>
        <TabsContent value="keys" className="flex flex-col gap-6">
          <KeysSection view={view} save={save} onView={setView} />
        </TabsContent>
        <TabsContent value="team">
          <TeamServerSection view={view} save={save} />
        </TabsContent>
        <TabsContent value="file">
          <FileSection view={view} onView={setView} />
        </TabsContent>
      </Tabs>
      <Dialog open={asking} onOpenChange={(open) => !open && answer.current?.(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Comments in casebench.yaml will be dropped</DialogTitle>
            <DialogDescription>
              Saving a section rewrites the file with its header, as casebench init does, so other comments go. To
              keep them, change the file in the File tab instead.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => answer.current?.(false)}>
              Cancel
            </Button>
            <Button onClick={() => answer.current?.(true)}>Save anyway</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

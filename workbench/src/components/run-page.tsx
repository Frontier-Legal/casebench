// The Run page: choose a suite, see what the run will send and cost, start it, follow it, and
// open its results; the run is `casebench run`, started by the workbench (decision 0063).

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { ChartColumnIcon, CircleStopIcon, InboxIcon, PlayIcon, RotateCwIcon, SettingsIcon } from "lucide-react"

import { Section, Status, Tile } from "@/components/section"
import { NumberField } from "@/components/settings/fields"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { api, type JobView, type RunAsked, type RunPlan, type SuiteChoice } from "@/lib/api"
import { plural } from "@/lib/words"

// How often a running run is asked what it printed: often enough to read as live.
const POLL_MS = 1000
// The plan is asked for once typing in a number stops, not on every keystroke.
const SETTLE_MS = 250
// casebench run's own defaults for --sample and --cases.
const SAMPLE = 20
const CASES = 10
const FIRST = "\0first"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const STATES: Record<JobView["state"], { tone: "good" | "bad" | "warn" | "none"; label: string }> = {
  running: { tone: "warn", label: "Running" },
  finished: { tone: "good", label: "Finished" },
  failed: { tone: "bad", label: "Stopped with an error" },
  stopped: { tone: "none", label: "Stopped" },
}

function useJob() {
  const [job, setJob] = useState<JobView | null | undefined>(undefined)
  const lines = useRef<string[]>([])
  const poll = useCallback(async () => {
    const found = await api.runCurrent(lines.current.length)
    if (found === null) {
      lines.current = []
      setJob(null)
      return null
    }
    // A new run starts its lines again.
    if (found.line_count < lines.current.length) lines.current = []
    lines.current = [...lines.current, ...found.lines]
    const whole = { ...found, lines: lines.current }
    setJob(whole)
    return whole
  }, [])
  const reset = () => {
    lines.current = []
  }
  return { job, poll, reset }
}

export function RunPage({ onReports, onQueue, onSettings }: { onReports: () => void; onQueue: () => void; onSettings: () => void }) {
  const [suites, setSuites] = useState<SuiteChoice[] | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const [sample, setSample] = useState<number | null>(SAMPLE)
  const [cases, setCases] = useState<number | null>(CASES)
  const [plan, setPlan] = useState<RunPlan | null>(null)
  const [planning, setPlanning] = useState(false)
  const [starting, setStarting] = useState(false)
  const { job, poll, reset } = useJob()
  const log = useRef<HTMLPreElement>(null)

  useEffect(() => {
    api
      .runSuites()
      .then((found) => {
        setSuites(found)
        setChosen((current) => current ?? (found[0] ? (found[0].first ? FIRST : found[0].suite_id) : null))
      })
      .catch((error) => toast.error(message(error)))
    poll().catch(() => {})
  }, [poll])

  const running = job?.state === "running"
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => poll().catch(() => {}), POLL_MS)
    return () => window.clearInterval(timer)
  }, [running, poll])

  useEffect(() => {
    log.current?.scrollTo?.({ top: log.current.scrollHeight })
  }, [job?.lines.length])

  const asked = useCallback((): RunAsked => {
    if (chosen === FIRST) return { suite_id: null, sample: sample ?? SAMPLE, cases: cases ?? CASES }
    return { suite_id: chosen }
  }, [chosen, sample, cases])

  useEffect(() => {
    if (chosen === null) return
    setPlan(null)
    setPlanning(true)
    const timer = window.setTimeout(() => {
      api
        .runPlan(asked())
        .then(setPlan)
        .catch((error) => toast.error(message(error)))
        .finally(() => setPlanning(false))
    }, SETTLE_MS)
    return () => window.clearTimeout(timer)
  }, [chosen, asked])

  async function start(what: RunAsked = asked()) {
    setStarting(true)
    try {
      reset()
      await api.runStart(what)
      await poll()
      toast.success("The run started")
    } catch (error) {
      toast.error(message(error))
    } finally {
      setStarting(false)
    }
  }

  async function stop() {
    if (!job) return
    try {
      await api.runStop(job.id)
      await poll()
    } catch (error) {
      toast.error(message(error))
    }
  }

  if (suites === null || job === undefined) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  const total = job?.total ?? null
  const answeredShare = total ? (job!.answered / total) * 100 : 0
  const scoredShare = total ? (job!.scored / total) * 100 : 0

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Run</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Send a suite to the agent and score its answers, as casebench run does in a terminal. Nothing is sent until you
          start.
        </p>
      </div>

      {job && (
        <Section
          title={`The run of ${job.title}`}
          description={<Status tone={STATES[job.state].tone}>{STATES[job.state].label}</Status>}
          action={
            running ? (
              <Button variant="outline" size="sm" onClick={stop}>
                <CircleStopIcon /> Stop
              </Button>
            ) : null
          }
          footer={
            job.state === "finished" ? (
              <div className="flex flex-wrap gap-2">
                <Button onClick={onReports}>
                  <ChartColumnIcon /> Open the report
                </Button>
                <Button variant="outline" onClick={onQueue}>
                  <InboxIcon /> Review the answers
                </Button>
              </div>
            ) : undefined
          }
        >
          <Card className="mb-4 py-3">
            <CardContent className="grid grid-cols-2 gap-2 px-3 sm:grid-cols-3">
              <Tile label="Run" value={<span className="font-mono text-sm">{job.run_id ?? "starting"}</span>} />
              <div className="flex min-w-0 flex-col gap-2 rounded-lg bg-muted/50 p-3">
                <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Answered</div>
                <div className="text-base font-semibold tabular-nums">
                  {job.answered}
                  {total ? ` of ${total}` : ""}
                </div>
                <Progress value={answeredShare} aria-label="Cases answered" />
              </div>
              <div className="flex min-w-0 flex-col gap-2 rounded-lg bg-muted/50 p-3">
                <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Scored</div>
                <div className="text-base font-semibold tabular-nums">
                  {job.scored}
                  {total ? ` of ${total}` : ""}
                </div>
                <Progress value={scoredShare} aria-label="Answers scored" />
              </div>
            </CardContent>
          </Card>
          {job.unscored > 0 && (
            <Alert variant="destructive" className="mb-4">
              <AlertTitle>{plural(job.unscored, "result")} could not be scored</AlertTitle>
              <AlertDescription>
                <p>
                  What went wrong is listed below, often a key that is not set. Fix it in Settings, then score what is
                  missing: nothing already answered or scored is sent again.
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={onSettings}>
                    <SettingsIcon /> Settings
                  </Button>
                  {!running && job.run_id && (
                    <Button
                      size="sm"
                      onClick={() => start({ suite_id: job.suite_id, run_id: job.run_id })}
                      disabled={starting}
                    >
                      <RotateCwIcon /> Score what is missing
                    </Button>
                  )}
                </div>
              </AlertDescription>
            </Alert>
          )}
          <pre
            ref={log}
            aria-label="What the run printed"
            className="max-h-96 overflow-auto rounded-lg bg-muted/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap"
          >
            {job.lines.join("\n") || "Starting…"}
          </pre>
        </Section>
      )}

      <Section title="What to run" description="A suite this project holds, or the first suite, built from the corpus.">
        {suites.length === 0 ? (
          <Alert>
            <AlertTitle>No suite to run</AlertTitle>
            <AlertDescription>
              <p>
                A first suite is built from the corpus when casebench.yaml has a corpus and two extraction models. Set them
                in Settings, or write cases in Golden data.
              </p>
              <Button variant="outline" size="sm" className="mt-2" onClick={onSettings}>
                <SettingsIcon /> Settings
              </Button>
            </AlertDescription>
          </Alert>
        ) : (
          <RadioGroup value={chosen ?? undefined} onValueChange={setChosen} aria-label="Suite" className="gap-2">
            {suites.map((suite) => {
              const value = suite.first ? FIRST : suite.suite_id
              return (
                <Label
                  key={value}
                  htmlFor={`suite-${value}`}
                  className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 font-normal has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-primary/5"
                >
                  <RadioGroupItem id={`suite-${value}`} value={value} className="mt-0.5" />
                  <span className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium">
                      {suite.first ? "Build the first suite from the corpus" : suite.suite_id}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {suite.first
                        ? "Two models read a sample of decisions; what both find becomes a case."
                        : `${plural(suite.cases, "case")} · ${suite.folder}`}
                    </span>
                  </span>
                </Label>
              )
            })}
          </RadioGroup>
        )}
        {chosen === FIRST && (
          <div className="mt-4 grid max-w-lg gap-4 sm:grid-cols-2">
            <NumberField label="Decisions to read" step="1" min={1} value={sample} onChange={setSample} />
            <NumberField label="Cases to make" step="1" min={1} value={cases} onChange={setCases} />
          </div>
        )}
      </Section>

      {chosen !== null && (
        <Section
          title="What the run will send"
          description="Counted before anything is sent. Each model's price is in Settings."
          footer={
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={() => start()} disabled={!plan?.can_start || starting || running}>
                {starting ? <Spinner /> : <PlayIcon />} Start the run
              </Button>
              {running && <span className="text-xs text-muted-foreground">A run is going; one runs at a time.</span>}
            </div>
          }
        >
          {planning || !plan ? (
            <Skeleton className="h-24" />
          ) : (
            <div className="flex flex-col gap-3">
              {plan.why_not && (
                <Alert variant="destructive">
                  <AlertTitle>This run cannot start</AlertTitle>
                  <AlertDescription>{plan.why_not.charAt(0).toUpperCase() + plan.why_not.slice(1)}.</AlertDescription>
                </Alert>
              )}
              {plan.lines.length > 0 && (
                <ul aria-label="Estimate" className="flex flex-col gap-1.5 text-sm">
                  {plan.lines.map((line, index) => (
                    <li key={index} className="whitespace-pre-wrap">
                      {line}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </Section>
      )}
    </div>
  )
}

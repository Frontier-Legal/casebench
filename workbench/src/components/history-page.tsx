// The History page: a suite's error rates and metrics run by run, by practice area, reference
// source and approval, never averaged across them, with the runs listed below (decision 0067).

import { useEffect, useId, useMemo, useState } from "react"
import { toast } from "sonner"
import { ArrowDownRightIcon, ArrowUpRightIcon, ChartLineIcon, MinusIcon } from "lucide-react"

import { day, percent, TrendChart } from "@/components/history/trend-chart"
import { Section } from "@/components/section"
import { Badge } from "@/components/ui/badge"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api, type History, type HistoryPoint, type HistoryRun, type SuiteHistory } from "@/lib/api"
import { message } from "@/lib/use-settings"
import { taskName } from "@/lib/words"

const EVERY_AREA = ""
const SOURCES: Record<string, string> = {
  court: "Court records",
  lawyer: "Lawyers' references",
  structured: "Structured references",
  hybrid: "Court and lawyer",
}
const APPROVALS: Record<string, string> = { approved: "Lawyer-approved cases", draft: "Unreviewed cases" }

function Picker({
  label,
  value,
  choices,
  onChange,
}: {
  label: string
  value: string
  choices: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  const id = useId()
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 min-w-44 rounded-md border border-input bg-background px-2 text-sm text-foreground shadow-xs focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </label>
  )
}

/** The latest value and how far it moved since the run before, in the measure's own terms. */
function Latest({ points, lowerIsBetter }: { points: HistoryPoint[]; lowerIsBetter: boolean }) {
  const last = points.at(-1)
  const before = points.at(-2)
  if (!last) return <span className="text-sm text-muted-foreground">Not measured</span>
  const moved = before ? Math.round((last.mean - before.mean) * 1000) / 10 : 0
  const better = lowerIsBetter ? moved < 0 : moved > 0
  const Icon = moved === 0 ? MinusIcon : moved > 0 ? ArrowUpRightIcon : ArrowDownRightIcon
  return (
    <div className="flex items-baseline gap-2" aria-label={`Latest: ${percent(last.mean)}`}>
      <span className="text-2xl font-semibold tracking-tight tabular-nums">{percent(last.mean)}</span>
      {before && (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Icon
            aria-hidden
            className={moved === 0 ? "size-3.5" : better ? "size-3.5 text-success" : "size-3.5 text-destructive"}
          />
          {moved === 0 ? "no change" : `${moved > 0 ? "+" : ""}${moved} points, ${better ? "better" : "worse"}`}
        </span>
      )}
    </div>
  )
}

function Values({ runs, points }: { runs: HistoryRun[]; points: HistoryPoint[] }) {
  const byRun = new Map(points.map((p) => [p.run_id, p]))
  return (
    <details className="text-xs">
      <summary className="cursor-pointer text-muted-foreground">Values</summary>
      <Table className="mt-2">
        <TableHeader>
          <TableRow>
            <TableHead>Run</TableHead>
            <TableHead className="text-right">Value</TableHead>
            <TableHead className="text-right">95% interval</TableHead>
            <TableHead className="text-right">Answers</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => {
            const point = byRun.get(run.run_id)
            return (
              <TableRow key={run.run_id}>
                <TableCell>{day(run.scored_at)}</TableCell>
                <TableCell className="text-right tabular-nums">{point ? percent(point.mean) : "–"}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {point ? `${percent(point.low)} to ${percent(point.high)}` : "–"}
                </TableCell>
                <TableCell className="text-right tabular-nums">{point?.n ?? "–"}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </details>
  )
}

function Measure({
  title,
  meaning,
  runs,
  points,
  moved,
  changes,
  lowerIsBetter,
}: {
  title: string
  meaning?: string
  runs: HistoryRun[]
  points: HistoryPoint[]
  moved?: string[]
  changes: Record<string, string[]>
  lowerIsBetter: boolean
}) {
  return (
    <article aria-label={title} className="flex flex-col gap-3 rounded-xl border bg-card p-4 shadow-xs">
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-medium">{title}</h3>
          <span className="text-xs text-muted-foreground">{lowerIsBetter ? "lower is better" : "higher is better"}</span>
        </div>
        {meaning && <p className="text-xs text-muted-foreground">{meaning}</p>}
      </div>
      <Latest points={points} lowerIsBetter={lowerIsBetter} />
      <TrendChart label={title} runs={runs} points={points} moved={moved} changes={changes} />
      <Values runs={runs} points={points} />
    </article>
  )
}

export function HistoryPage() {
  const [suites, setSuites] = useState<SuiteHistory[] | null>(null)
  const [suite, setSuite] = useState<string | null>(null)
  const [history, setHistory] = useState<History | null>(null)
  const [area, setArea] = useState(EVERY_AREA)
  const [source, setSource] = useState<string | null>(null)
  const [approval, setApproval] = useState<string | null>(null)

  useEffect(() => {
    api
      .histories()
      .then((found) => {
        setSuites(found)
        setSuite(found[0]?.suite_id ?? null)
      })
      .catch((error) => toast.error(message(error)))
  }, [])

  useEffect(() => {
    setHistory(null)
    if (!suite) return
    api
      .history(suite)
      .then((found) => {
        setHistory(found)
        const sources = [...new Set(found.series.map((s) => s.reference_source))]
        const approvals = [...new Set(found.series.map((s) => s.approval))]
        setSource(sources[0] ?? null)
        setApproval(approvals.includes("approved") ? "approved" : (approvals[0] ?? null))
        setArea(EVERY_AREA)
      })
      .catch((error) => toast.error(message(error)))
  }, [suite])

  const options = useMemo(() => {
    const series = history?.series ?? []
    return {
      sources: [...new Set(series.map((s) => s.reference_source))],
      approvals: [...new Set(series.map((s) => s.approval))],
      areas: [...new Set(series.flatMap((s) => (s.practice_area ? [s.practice_area] : [])))].sort(),
    }
  }, [history])

  if (suites === null) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-64" />
      </div>
    )
  }
  if (!suites.length) {
    return (
      <Empty className="mt-10 border md:mt-20">
        <EmptyHeader>
          <EmptyMedia variant="icon" className="bg-brand-soft text-primary">
            <ChartLineIcon />
          </EmptyMedia>
          <EmptyTitle>No history yet</EmptyTitle>
          <EmptyDescription>
            Each scored run of a suite adds a point here. Run a suite again tomorrow, or every night, and each
            metric shows how it moved.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const changes = Object.fromEntries((history?.runs ?? []).map((run) => [run.run_id, run.changed]))
  const shown = (history?.series ?? []).filter(
    (s) =>
      s.reference_source === source &&
      s.approval === approval &&
      (area === EVERY_AREA ? s.practice_area === null : s.practice_area === area),
  )

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">History</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          How each measure moved from run to run of a suite, with its 95% interval. Lawyers' verdicts count in place
          of the judge's. A diamond marks a run whose settings, such as its judge, moved that measure, so the runs on
          either side do not compare.
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-3" aria-label="What the charts show">
        <Picker
          label="Suite"
          value={suite ?? ""}
          choices={suites.map((s) => ({ value: s.suite_id, label: `${s.suite_id} · ${s.runs} runs` }))}
          onChange={setSuite}
        />
        <Picker
          label="Practice area"
          value={area}
          choices={[{ value: EVERY_AREA, label: "Every practice area" }, ...options.areas.map((a) => ({ value: a, label: a }))]}
          onChange={setArea}
        />
        {options.sources.length > 1 && (
          <Picker
            label="Reference"
            value={source ?? ""}
            choices={options.sources.map((s) => ({ value: s, label: SOURCES[s] ?? s }))}
            onChange={setSource}
          />
        )}
        {options.approvals.length > 1 && (
          <Picker
            label="Cases"
            value={approval ?? ""}
            choices={options.approvals.map((a) => ({ value: a, label: APPROVALS[a] ?? a }))}
            onChange={setApproval}
          />
        )}
        {history && (
          <Badge variant="secondary" className="mb-2">
            {history.runs.length} runs · {day(history.runs[0]?.scored_at ?? null)} to{" "}
            {day(history.runs.at(-1)?.scored_at ?? null)}
          </Badge>
        )}
      </div>
      {!history ? (
        <Skeleton className="h-96" />
      ) : (
        <>
          <section aria-label="Error rates" className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">Error rates, every case</h2>
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
              {history.rates.map((rate) => (
                <Measure
                  key={rate.error}
                  title={rate.error.charAt(0).toUpperCase() + rate.error.slice(1)}
                  meaning={rate.meaning}
                  runs={history.runs}
                  points={rate.points}
                  changes={changes}
                  lowerIsBetter
                />
              ))}
            </div>
          </section>
          <section aria-label="Metrics" className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">
              Metrics · {SOURCES[source ?? ""] ?? source} · {APPROVALS[approval ?? ""] ?? approval}
              {area ? ` · ${area}` : ""}
            </h2>
            {shown.length ? (
              <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {shown.map((s) => (
                  <Measure
                    key={`${s.task_type}:${s.metric}`}
                    title={s.name}
                    meaning={taskName(s.task_type)}
                    runs={history.runs}
                    points={s.points}
                    moved={s.moved}
                    changes={changes}
                    lowerIsBetter={s.direction === "lower"}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No metric was measured for these cases.</p>
            )}
          </section>
          <Section title="Runs" description="Every scored run of the suite, oldest first, and what changed at each.">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Scored</TableHead>
                  <TableHead>Run</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Commit</TableHead>
                  <TableHead>Changed since the run before</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.runs.map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell className="whitespace-nowrap">{day(run.scored_at)}</TableCell>
                    <TableCell className="font-mono text-xs">{run.run_id}</TableCell>
                    <TableCell>{run.target}</TableCell>
                    <TableCell className="font-mono text-xs">{run.commit?.slice(0, 7) ?? "–"}</TableCell>
                    <TableCell>{run.changed.join(", ") || "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Section>
        </>
      )}
    </div>
  )
}

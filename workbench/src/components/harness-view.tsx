import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Section, Status, Tile } from "@/components/section"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { api, type Authority, type Bar, type Harness, type RunRow, type StepDiff, type Total } from "@/lib/api"
import { cn } from "@/lib/utils"

const NONE = "none"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function ms(value: number | null | undefined): string {
  if (value == null) return "–"
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`
}

function count(value: number | null | undefined): string {
  return value == null ? "–" : value.toLocaleString()
}

function dollars(value: number | null | undefined): string {
  if (value == null) return "–"
  return value >= 0.01 || value === 0 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`
}

const COLOURS: Record<string, string> = {
  llm: "bg-primary",
  tool: "bg-chart-2",
  retrieval: "bg-chart-3",
  rerank: "bg-chart-3",
  document: "bg-chart-4",
}

function label(bar: Bar): string {
  if (bar.unaccounted) return "Unaccounted"
  return bar.name ?? bar.kind
}

/** Each call as a bar placed by its start; time no call covers is drawn, not hidden. */
function Waterfall({ harness }: { harness: Harness }) {
  const total = Math.max(harness.span_ms ?? 0, harness.latency_ms ?? 0, 1)
  const timed = harness.bars.filter((b) => b.at_ms != null)
  const untimed = harness.bars.filter((b) => b.at_ms == null)
  return (
    <div className="flex flex-col gap-1" role="list" aria-label="Waterfall">
      {timed.map((bar) => (
        <div
          key={bar.number}
          role="listitem"
          data-unaccounted={bar.unaccounted || undefined}
          className="grid grid-cols-1 gap-1 rounded-md px-2 py-1.5 text-sm hover:bg-muted/50 md:grid-cols-[13rem_minmax(0,1fr)_17rem] md:items-center md:gap-3"
        >
          <div className="flex min-w-0 items-start gap-2">
            <span className="w-6 shrink-0 pt-px text-right text-xs text-muted-foreground tabular-nums">{bar.number}</span>
            <div className="flex min-w-0 flex-col">
              <span
                className={cn("truncate", bar.unaccounted ? "text-muted-foreground" : "font-medium")}
                title={label(bar)}
              >
                {label(bar)}
              </span>
              {bar.model && <span className="truncate text-xs text-muted-foreground">{bar.model}</span>}
            </div>
          </div>
          <div className="relative h-5 rounded bg-muted/60" aria-hidden>
            <div
              className={cn(
                "absolute inset-y-0.5 min-w-[3px] rounded-sm",
                bar.unaccounted
                  ? "border border-dashed border-warning bg-[repeating-linear-gradient(135deg,transparent_0_4px,var(--color-warning)_4px_5px)] opacity-80"
                  : (COLOURS[bar.kind] ?? "bg-chart-2"),
              )}
              style={{
                left: `${((bar.at_ms ?? 0) / total) * 100}%`,
                width: `${((bar.duration_ms ?? 0) / total) * 100}%`,
              }}
            />
          </div>
          <div className="flex gap-3 text-xs text-muted-foreground tabular-nums md:justify-end">
            <span className="font-medium text-foreground">{ms(bar.duration_ms)}</span>
            {bar.unaccounted ? (
              <span>no step accounts for it</span>
            ) : (
              <>
                {(bar.input_tokens != null || bar.output_tokens != null) && (
                  <span>
                    {count(bar.input_tokens)} in · {count(bar.output_tokens)} out
                  </span>
                )}
                {bar.kind === "llm" && <span>{bar.cost == null ? "no price" : `≈ ${dollars(bar.cost)}`}</span>}
                {bar.arguments && (
                  <span className="max-w-[12rem] truncate" title={bar.arguments}>
                    {bar.arguments}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      ))}
      {harness.outside_ms > 0 && (
        <div
          role="listitem"
          data-unaccounted
          className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm text-muted-foreground"
        >
          <span>Unaccounted, outside the recorded steps</span>
          <span className="shrink-0 font-medium whitespace-nowrap text-foreground tabular-nums">{ms(harness.outside_ms)}</span>
        </div>
      )}
      {untimed.length > 0 && (
        <p className="px-2 pt-2 text-xs text-muted-foreground">
          {untimed.length} more {untimed.length === 1 ? "step was" : "steps were"} recorded without times:{" "}
          {untimed.map((b) => label(b)).join(", ")}.
        </p>
      )}
    </div>
  )
}

function Totals({ title, rows }: { title: string; rows: Total[] }) {
  return (
    <Table aria-label={title}>
      <TableHeader>
        <TableRow>
          <TableHead>{title}</TableHead>
          <TableHead className="text-right">Calls</TableHead>
          <TableHead className="text-right">Tokens in</TableHead>
          <TableHead className="text-right">Tokens out</TableHead>
          <TableHead className="text-right">Cost (est.)</TableHead>
          <TableHead className="text-right">Time</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.name}>
            <TableCell className="font-medium">{row.name}</TableCell>
            <TableCell className="text-right tabular-nums">{row.calls}</TableCell>
            <TableCell className="text-right tabular-nums">{count(row.input_tokens)}</TableCell>
            <TableCell className="text-right tabular-nums">{count(row.output_tokens)}</TableCell>
            <TableCell className="text-right tabular-nums">{dollars(row.cost)}</TableCell>
            <TableCell className="text-right tabular-nums">{ms(row.duration_ms)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Stage({ at, checked, moot }: { at: number | boolean | null; checked: boolean; moot?: boolean }) {
  if (!checked) return <span className="text-xs text-muted-foreground">not checked</span>
  if (moot) return <span className="text-xs text-muted-foreground">–</span>
  if (at === null || at === false) return <Status tone="bad">no</Status>
  return <Status tone="good">{at === true ? "yes" : `step ${at}`}</Status>
}

const STAGES: { key: keyof Authority; title: string }[] = [
  { key: "retrieved", title: "Retrieved" },
  { key: "kept", title: "Kept" },
  { key: "read", title: "Read" },
  { key: "cited", title: "Cited" },
  { key: "characterised", title: "Characterised" },
]

function Funnel({ rows, label: name }: { rows: Authority[]; label: string }) {
  return (
    <Table aria-label={name}>
      <TableHeader>
        <TableRow>
          <TableHead>Court authority</TableHead>
          {STAGES.map((s) => (
            <TableHead key={s.key}>{s.title}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.document_id}>
            <TableCell className="font-medium">{row.document_id}</TableCell>
            {STAGES.map((s) => (
              <TableCell key={s.key}>
                <Stage
                  at={row[s.key] as number | boolean | null}
                  checked={row.checked.includes(s.key as string)}
                  moot={s.key === "characterised" && row.cited === false}
                />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

const CHANGE_TONES: Record<string, "good" | "bad" | "warn" | "none"> = {
  slower: "bad",
  "more tokens": "warn",
  gone: "bad",
  new: "warn",
  faster: "good",
  "fewer tokens": "good",
  same: "none",
}

function Diff({ rows, against }: { rows: StepDiff[]; against: string }) {
  return (
    <Table aria-label="Steps against the other run">
      <TableHeader>
        <TableRow>
          <TableHead>Step</TableHead>
          <TableHead className="text-right">Time in {against}</TableHead>
          <TableHead className="text-right">Time here</TableHead>
          <TableHead className="text-right">Tokens in {against}</TableHead>
          <TableHead className="text-right">Tokens here</TableHead>
          <TableHead>Change</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.step}>
            <TableCell className="font-medium">{row.step}</TableCell>
            <TableCell className="text-right tabular-nums">{ms(row.before_ms)}</TableCell>
            <TableCell className="text-right tabular-nums">{ms(row.after_ms)}</TableCell>
            <TableCell className="text-right tabular-nums">{count(row.before_tokens)}</TableCell>
            <TableCell className="text-right tabular-nums">{count(row.after_tokens)}</TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-x-3 gap-y-1">
                {row.changes.map((change) => (
                  <Status key={change} tone={CHANGE_TONES[change] ?? "none"}>
                    {change}
                  </Status>
                ))}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/** The answer's harness for engineers: the waterfall, sums, the authority funnel by step, and
 * a diff against the same case in another run (decision 0056). */
export function HarnessView({ itemKey }: { itemKey: string }) {
  const [, runId, caseId, repeat] = itemKey.split(":").map(decodeURIComponent)
  const [runs, setRuns] = useState<RunRow[]>([])
  const [against, setAgainst] = useState<string | null>(null)
  const [harness, setHarness] = useState<Harness | null>(null)

  useEffect(() => {
    api.runs().then(setRuns).catch(() => {})
  }, [])

  useEffect(() => {
    setHarness(null)
    api
      .harness(runId, caseId, Number(repeat), against)
      .then(setHarness)
      .catch((error) => toast.error(message(error)))
  }, [runId, caseId, repeat, against])

  const suite = runs.find((r) => r.run_id === runId)?.suite_id
  const others = runs.filter((r) => r.run_id !== runId && r.suite_id === suite)
  const cost = harness?.bars.reduce((sum, b) => sum + (b.cost ?? 0), 0) ?? 0

  return (
    <Section
      title="Harness"
      description="Each step the agent took, in time order. Costs are estimates at the prices in casebench.yaml. Reviewers do not see this."
      className="mt-6"
      data-testid="harness"
      action={
        others.length > 0 && (
          <div className="flex items-center gap-2">
            <Label htmlFor="harness-against" className="hidden text-xs text-muted-foreground sm:inline">
              Compare with
            </Label>
            <Select value={against ?? NONE} onValueChange={(value) => setAgainst(value === NONE ? null : value)}>
              <SelectTrigger id="harness-against" size="sm" className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end">
                <SelectItem value={NONE}>No other run</SelectItem>
                {others.map((r) => (
                  <SelectItem key={r.run_id} value={r.run_id}>
                    {r.run_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )
      }
    >
      {harness === null ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Tile label="Latency" value={ms(harness.latency_ms)} />
            <Tile label="Recorded span" value={ms(harness.span_ms)} />
            <Tile
              label="Unaccounted"
              value={ms(harness.unaccounted_ms)}
              caption={harness.unaccounted_ms > 0 ? "Time no step covers" : "Every moment is covered"}
            />
            <Tile
              label="Agent cost (est.)"
              value={harness.priced ? dollars(cost) : "No price"}
              caption={harness.priced ? "At the configured prices" : "A model has no price"}
            />
          </div>
          {harness.bars.length === 0 ? (
            <p className="text-sm text-muted-foreground">The run recorded no steps for this answer.</p>
          ) : (
            <Waterfall harness={harness} />
          )}
          {harness.against && (
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">Against run {harness.against}</h3>
              <Diff rows={harness.diff} against={harness.against} />
            </div>
          )}
          {harness.funnel !== null && (
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold">Where each court authority went</h3>
              {!harness.funnel_possible ? (
                <p className="text-sm text-muted-foreground">
                  No funnel is possible: no step recorded the document ids it returned.
                </p>
              ) : (
                <>
                  <Funnel rows={harness.funnel} label="Authority funnel" />
                  {harness.funnel_before && harness.against && (
                    <>
                      <h4 className="text-xs font-medium text-muted-foreground">In run {harness.against}</h4>
                      <Funnel rows={harness.funnel_before} label="Authority funnel in the other run" />
                    </>
                  )}
                </>
              )}
            </div>
          )}
          <Totals title="Step" rows={harness.by_step} />
          {harness.by_model.length > 0 && <Totals title="Model" rows={harness.by_model} />}
        </div>
      )}
    </Section>
  )
}

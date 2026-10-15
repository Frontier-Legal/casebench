import { useEffect, useState } from "react"
import { toast } from "sonner"
import { ChartColumnIcon, ChevronRightIcon, DownloadIcon, FileCodeIcon, FileIcon, FileTextIcon } from "lucide-react"

import { Section } from "@/components/section"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { api, downloadReport, type ExportKind, type RateView, type RunReport, type RunRow } from "@/lib/api"
import { plural } from "@/lib/words"
import { cn } from "@/lib/utils"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const EXPORTS: { kind: ExportKind; label: string; hint: string; icon: typeof FileIcon }[] = [
  { kind: "pdf", label: "PDF", hint: "To read and to send", icon: FileIcon },
  { kind: "docx", label: "Word", hint: "To edit before sending", icon: FileTextIcon },
  { kind: "html", label: "Web page, one file", hint: "Opens in any browser, offline", icon: FileCodeIcon },
]

function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

function RateCard({
  rate,
  chosen,
  onChoose,
}: {
  rate: RateView
  chosen: boolean
  onChoose: () => void
}) {
  return (
    <button
      type="button"
      onClick={onChoose}
      aria-pressed={chosen}
      className={cn(
        "flex min-w-0 flex-col gap-1.5 rounded-xl border bg-card p-4 text-left shadow-xs transition-colors outline-none",
        "hover:bg-muted/50 focus-visible:ring-[3px] focus-visible:ring-ring/50",
        chosen && "border-foreground/40 bg-muted/60",
      )}
    >
      <span className="text-sm font-medium first-letter:uppercase">
        {rate.error}
      </span>
      <span className="text-2xl font-semibold tracking-tight tabular-nums">
        {percent(rate.rate)}
      </span>
      <span className="text-xs text-muted-foreground tabular-nums">
        {rate.failing.length} of {plural(rate.n, "answer")} · 95% interval{" "}
        {percent(rate.low)} to {percent(rate.high)}
      </span>
      <span className="text-xs text-muted-foreground">
        The answer {rate.meaning}.
      </span>
    </button>
  )
}

/** A run's error rates, each opening the answers that have the error beside their evidence
 * (decision 0054). */
export function Reports({ onOpen }: { onOpen: (key: string) => void }) {
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [runId, setRunId] = useState<string | null>(null)
  const [report, setReport] = useState<RunReport | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  async function save(kind: ExportKind) {
    if (!runId) return
    setExporting(true)
    try {
      toast.success(`Saved ${await downloadReport(runId, kind)}`)
    } catch (error) {
      toast.error(message(error))
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    api
      .runs()
      .then((found) => {
        setRuns(found)
        setRunId(found.find((r) => r.scored)?.run_id ?? null)
      })
      .catch((error) => toast.error(message(error)))
  }, [])

  useEffect(() => {
    if (!runId) return
    setReport(null)
    api
      .runReport(runId)
      .then((found) => {
        setReport(found)
        setChosen(found.rates.find((r) => r.failing.length)?.error ?? null)
      })
      .catch((error) => toast.error(message(error)))
  }, [runId])

  if (runs === null) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-32" />
      </div>
    )
  }

  const scored = runs.filter((r) => r.scored)
  const rate = report?.rates.find((r) => r.error === chosen) ?? null

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
            Reports
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            How often the agent gets the law wrong in a run. Each rate opens the
            answers with the error, beside the court record or the lawyer's
            reference. Lawyers' verdicts count in place of the judge's.
          </p>
        </div>
        {scored.length > 0 && (
          <div className="flex items-end gap-2">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5 md:w-72 md:flex-none">
            <Label htmlFor="report-run">Run</Label>
            <Select value={runId ?? undefined} onValueChange={setRunId}>
              <SelectTrigger id="report-run" className="w-full">
                <SelectValue placeholder="Choose a run" />
              </SelectTrigger>
              <SelectContent>
                {scored.map((r) => (
                  <SelectItem key={r.run_id} value={r.run_id}>
                    {r.run_id} · {r.suite_id} · {r.target}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" disabled={!runId || exporting}>
                  {exporting ? <Spinner /> : <DownloadIcon />} Export for partners
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuLabel>The report for partners</DropdownMenuLabel>
                {EXPORTS.map((e) => (
                  <DropdownMenuItem key={e.kind} onSelect={() => save(e.kind)}>
                    <e.icon />
                    <div className="flex flex-col">
                      <span>{e.label}</span>
                      <span className="text-xs text-muted-foreground">{e.hint}</span>
                    </div>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>
      {scored.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ChartColumnIcon />
            </EmptyMedia>
            <EmptyTitle>No scored run yet</EmptyTitle>
            <EmptyDescription>
              A run's report appears here once your team runs the AI on a suite
              and scores it.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : report === null ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }, (_, n) => (
            <Skeleton key={n} className="h-36" />
          ))}
        </div>
      ) : report.rates.length === 0 ? (
        <Card>
          <CardContent className="text-sm text-muted-foreground">
            This run has no scores that show these errors: no citation check,
            outcome or statute metric scored it.
          </CardContent>
        </Card>
      ) : (
        <>
          <div
            className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
            aria-label="Error rates"
          >
            {report.rates.map((r) => (
              <RateCard
                key={r.error}
                rate={r}
                chosen={r.error === chosen}
                onChoose={() => setChosen(r.error)}
              />
            ))}
          </div>
          {rate && (
            <Section
              title={`Answers with ${/^[aeiou]/.test(rate.error) ? "an" : "a"} ${rate.error}`}
              description={
                rate.failing.length
                  ? `${plural(rate.failing.length, "answer")} of ${rate.n}. Open one to read it beside its evidence, and overrule the judge where it is wrong.`
                  : `None of the ${plural(rate.n, "answer")} has this error.`
              }
            >
              {rate.failing.length > 0 && (
                <ItemGroup
                  aria-label={`Answers with ${rate.error}`}
                  className="gap-2"
                >
                  {rate.failing.map((answer) => (
                    <div role="listitem" key={answer.key}>
                      <Item variant="muted" size="sm" asChild>
                        <button
                          type="button"
                          onClick={() => onOpen(answer.key)}
                          className="w-full text-left"
                        >
                          <ItemContent>
                            <ItemTitle className="line-clamp-2">
                              {answer.title}
                            </ItemTitle>
                            <ItemDescription>
                              Case {answer.case_id}
                              {answer.repeat
                                ? ` · repeat ${answer.repeat + 1}`
                                : ""}
                            </ItemDescription>
                          </ItemContent>
                          <ItemActions>
                            <ChevronRightIcon className="size-4 text-muted-foreground" />
                          </ItemActions>
                        </button>
                      </Item>
                    </div>
                  ))}
                </ItemGroup>
              )}
            </Section>
          )}
        </>
      )}
    </div>
  )
}

import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { ChevronLeftIcon, ChevronRightIcon, EyeIcon, GitCompareArrowsIcon } from "lucide-react"

import { FinishBar } from "@/components/finish-bar"
import { InputsCard } from "@/components/inputs-card"
import { Overline, Section, Status } from "@/components/section"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Kbd } from "@/components/ui/kbd"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api, type AreaView, type Comparison, type Pair, type RunRow, type Shown } from "@/lib/api"
import { factKind, plural } from "@/lib/words"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

const CHOICES: { value: Shown; label: string; key: string }[] = [
  { value: "a", label: "A is better", key: "A" },
  { value: "b", label: "B is better", key: "B" },
  { value: "equal", label: "Equal", key: "E" },
]

function signed(value: number): string {
  return `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(2)}`
}

function Summary({ areas, done, total }: { areas: AreaView[]; done: number; total: number }) {
  return (
    <Section
      title="The later run against the earlier"
      description="Per practice area: the later run's wins, losses and ties. The difference is wins minus losses per pair, with its 95% interval."
      action={
        <span className="text-xs whitespace-nowrap text-muted-foreground tabular-nums">
          {done} of {plural(total, "pair")} compared
        </span>
      }
    >
      <div className="flex flex-col gap-4">
        <Progress value={total ? (done / total) * 100 : 0} aria-label="Pairs compared" />
        {areas.length === 0 ? (
          <p className="text-sm text-muted-foreground">No preference given yet.</p>
        ) : (
          <Table aria-label="Preferences by practice area">
            <TableHeader>
              <TableRow>
                <TableHead>Practice area</TableHead>
                <TableHead className="text-right">Wins</TableHead>
                <TableHead className="text-right">Losses</TableHead>
                <TableHead className="text-right">Ties</TableHead>
                <TableHead className="text-right">Difference</TableHead>
                <TableHead>Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {areas.map((area) => (
                <TableRow key={area.practice_area ?? ""}>
                  <TableCell className="font-medium">{area.practice_area ?? "No practice area"}</TableCell>
                  <TableCell className="text-right tabular-nums">{area.wins}</TableCell>
                  <TableCell className="text-right tabular-nums">{area.losses}</TableCell>
                  <TableCell className="text-right tabular-nums">{area.ties}</TableCell>
                  <TableCell className="text-right whitespace-nowrap tabular-nums">
                    {signed(area.mean)}{" "}
                    <span className="text-muted-foreground">
                      [{signed(area.low)}, {signed(area.high)}]
                    </span>
                  </TableCell>
                  <TableCell>
                    {area.significant ? (
                      <Status tone={area.mean > 0 ? "good" : "bad"}>
                        {area.mean > 0 ? "Later run better" : "Earlier run better"}
                      </Status>
                    ) : (
                      <Status tone="none">Not significant</Status>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </Section>
  )
}

function AnswerCard({ letter, text }: { letter: string; text: string | null }) {
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
            {letter}
          </span>
          Answer {letter}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {text ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        ) : (
          <p className="text-sm text-muted-foreground">No answer.</p>
        )}
      </CardContent>
    </Card>
  )
}

/** Two runs compared blind: answers as A and B, a preference with a reason, and the later
 * run's wins, losses and ties per practice area (decision 0054). */
export function CompareRuns({ onHelp }: { onHelp: () => void }) {
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [first, setFirst] = useState<string | null>(null)
  const [second, setSecond] = useState<string | null>(null)
  const [comparison, setComparison] = useState<Comparison | null>(null)
  const [at, setAt] = useState(0)
  const [pair, setPair] = useState<Pair | null>(null)
  const [choice, setChoice] = useState<Shown | null>(null)
  const [reason, setReason] = useState("")
  const [busy, setBusy] = useState(false)
  const [missing, setMissing] = useState<string | null>(null)

  useEffect(() => {
    api
      .runs()
      .then((found) => {
        setRuns(found)
        const later = found[0]
        const earlier = later && found.find((r) => r.run_id !== later.run_id && r.suite_id === later.suite_id)
        if (later && earlier) {
          setSecond(later.run_id)
          setFirst(earlier.run_id)
        }
      })
      .catch((error) => toast.error(message(error)))
  }, [])

  const load = useCallback(async (earlier: string, later: string) => {
    const found = await api.comparison(earlier, later)
    setComparison(found)
    return found
  }, [])

  useEffect(() => {
    if (!first || !second) return
    setComparison(null)
    setPair(null)
    load(first, second)
      .then((found) => setAt(Math.max(0, found.pairs.findIndex((p) => !p.given))))
      .catch((error) => toast.error(message(error)))
  }, [first, second, load])

  const current = comparison?.pairs[at] ?? null
  useEffect(() => {
    if (!first || !second || !current) return
    setPair(null)
    setChoice(null)
    setReason("")
    setMissing(null)
    api
      .pair(first, second, current.case_id, current.repeat)
      .then(setPair)
      .catch((error) => toast.error(message(error)))
  }, [first, second, current])

  const left = useMemo(() => comparison?.pairs.filter((p) => !p.given).length ?? 0, [comparison])

  const give = useCallback(async () => {
    if (!first || !second || !current || busy) return
    if (!choice) return setMissing("Choose A, B or Equal first.")
    if (!reason.trim()) return setMissing("Say why. Your reason is kept with the preference.")
    setBusy(true)
    try {
      await api.prefer(first, second, current.case_id, current.repeat, choice, reason)
      toast.success("Preference recorded")
      const found = await load(first, second)
      const next = found.pairs.findIndex((p, n) => n > at && !p.given)
      const wrapped = next >= 0 ? next : found.pairs.findIndex((p) => !p.given)
      // With every pair compared, the open pair stays, its runs now named.
      if (wrapped >= 0) setAt(wrapped)
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }, [first, second, current, busy, choice, reason, load, at])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        give()
        return
      }
      if (typing(event.target)) {
        if (event.key === "Escape") (event.target as HTMLElement).blur()
        return
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return
      const picked = CHOICES.find((c) => c.key.toLowerCase() === event.key.toLowerCase())
      if (picked && pair && !pair.given) {
        event.preventDefault()
        setChoice(picked.value)
        setMissing(null)
      } else if (event.key === "?") {
        event.preventDefault()
        onHelp()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [give, pair, onHelp])

  if (runs === null) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  const suite = runs.find((r) => r.run_id === second)?.suite_id
  const earlier = runs.filter((r) => r.run_id !== second && r.suite_id === suite)
  const pickable = runs.filter((r) => runs.some((o) => o.run_id !== r.run_id && o.suite_id === r.suite_id))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Compare runs</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Read two answers to each case without knowing which run wrote which, and say which is better and
            why. The runs are named only after you choose.
          </p>
        </div>
        {pickable.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 lg:w-[34rem]">
            <div className="flex min-w-0 flex-col gap-1.5">
              <Label htmlFor="compare-second">Later run</Label>
              <Select
                value={second ?? undefined}
                onValueChange={(value) => {
                  setSecond(value)
                  const chosen = runs.find((r) => r.run_id === value)
                  setFirst(runs.find((r) => r.run_id !== value && r.suite_id === chosen?.suite_id)?.run_id ?? null)
                }}
              >
                <SelectTrigger id="compare-second" className="w-full">
                  <SelectValue placeholder="Choose a run" />
                </SelectTrigger>
                <SelectContent>
                  {pickable.map((r) => (
                    <SelectItem key={r.run_id} value={r.run_id}>
                      {r.run_id} · {r.suite_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex min-w-0 flex-col gap-1.5">
              <Label htmlFor="compare-first">Earlier run</Label>
              <Select value={first ?? undefined} onValueChange={setFirst}>
                <SelectTrigger id="compare-first" className="w-full">
                  <SelectValue placeholder="Choose a run" />
                </SelectTrigger>
                <SelectContent>
                  {earlier.map((r) => (
                    <SelectItem key={r.run_id} value={r.run_id}>
                      {r.run_id} · {r.suite_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </div>
      {pickable.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <GitCompareArrowsIcon />
            </EmptyMedia>
            <EmptyTitle>Two runs of one suite are needed</EmptyTitle>
            <EmptyDescription>
              When your team runs the AI on the same suite again, for example after changing the agent, the two
              runs can be compared here.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : comparison === null ? (
        <Skeleton className="h-64" />
      ) : comparison.pairs.length === 0 ? (
        <Alert>
          <AlertTitle>Nothing to compare</AlertTitle>
          <AlertDescription>The two runs did not answer any case in common.</AlertDescription>
        </Alert>
      ) : (
        <>
          <Summary areas={comparison.areas} done={comparison.pairs.length - left} total={comparison.pairs.length} />
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              aria-label="Previous pair"
              disabled={at === 0}
              onClick={() => setAt((n) => n - 1)}
            >
              <ChevronLeftIcon />
            </Button>
            <div className="min-w-0 flex-1 text-center text-sm">
              <span className="font-medium">
                Pair {at + 1} of {comparison.pairs.length}
              </span>
              {current?.practice_area && <span className="text-muted-foreground"> · {current.practice_area}</span>}
              {current?.given && <span className="text-muted-foreground"> · compared</span>}
            </div>
            <Button
              variant="outline"
              size="icon"
              aria-label="Next pair"
              disabled={at >= comparison.pairs.length - 1}
              onClick={() => setAt((n) => n + 1)}
            >
              <ChevronRightIcon />
            </Button>
          </div>
          {pair === null ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <Skeleton className="h-64" />
              <Skeleton className="h-64" />
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              <InputsCard inputs={pair.inputs} title="The question" />
              <div className="grid gap-6 lg:grid-cols-2" aria-label="Answers">
                <AnswerCard letter="A" text={pair.a} />
                <AnswerCard letter="B" text={pair.b} />
              </div>
              {pair.reference.length > 0 && (
                <Section title="Checked against" description="The court's findings or the lawyer's answer key">
                  <ul className="grid gap-2 md:grid-cols-2">
                    {pair.reference.map((fact) => (
                      <li key={fact.id} className="flex flex-col gap-1 rounded-lg bg-muted/50 p-3">
                        <Overline>{factKind(fact.kind)}</Overline>
                        <div className="text-sm font-medium">{fact.value}</div>
                        {fact.quote && <div className="text-sm text-muted-foreground">“{fact.quote}”</div>}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}
              {pair.given ? (
                <Alert>
                  <EyeIcon />
                  <AlertTitle>
                    {pair.given.choice === "equal"
                      ? "Judged equal"
                      : `${pair.given.choice.toUpperCase()} judged better`}{" "}
                    by {pair.given.by}
                  </AlertTitle>
                  <AlertDescription>
                    <p>
                      A was run {pair.given.a_run}
                      {pair.given.a_run === comparison.second ? " (later)" : " (earlier)"}; B was run{" "}
                      {pair.given.b_run}
                      {pair.given.b_run === comparison.second ? " (later)" : " (earlier)"}.
                    </p>
                    <p>“{pair.given.reason}”</p>
                  </AlertDescription>
                </Alert>
              ) : (
                <Section title="Which answer is better?">
                  <div className="flex flex-col gap-4">
                    <ToggleGroup
                      type="single"
                      variant="outline"
                      spacing={2}
                      aria-label="Your preference"
                      value={choice ?? ""}
                      onValueChange={(value) => {
                        if (value) setChoice(value as Shown)
                        setMissing(null)
                      }}
                      className="w-full sm:w-auto"
                    >
                      {CHOICES.map((c) => (
                        <ToggleGroupItem
                          key={c.value}
                          value={c.value}
                          aria-label={c.label}
                          className="h-10 flex-1 gap-1.5 bg-background px-3 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground sm:h-8 sm:flex-none"
                        >
                          {c.label}
                          <Kbd className="ml-0.5 hidden in-data-[state=on]:bg-primary-foreground/15 in-data-[state=on]:text-primary-foreground md:inline-flex">
                            {c.key}
                          </Kbd>
                        </ToggleGroupItem>
                      ))}
                    </ToggleGroup>
                    <Field data-invalid={Boolean(missing)}>
                      <FieldLabel htmlFor="compare-reason">Why?</FieldLabel>
                      <Textarea
                        id="compare-reason"
                        value={reason}
                        onChange={(event) => {
                          setReason(event.target.value)
                          setMissing(null)
                        }}
                        placeholder="For example: B cites the article in force; A relies on the repealed one."
                        rows={3}
                      />
                      <FieldDescription className={missing ? "text-destructive" : undefined}>
                        {missing ?? "Required. Kept with your name beside the later run."}
                      </FieldDescription>
                    </Field>
                  </div>
                </Section>
              )}
              {!pair.given && (
                <FinishBar
                  summary={choice ? CHOICES.find((c) => c.value === choice)!.label : "Choose A, B or Equal"}
                  left={left}
                  busy={busy}
                  onFinish={give}
                  label="Give preference and next"
                  unit="pair"
                  last="The last pair to compare"
                />
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

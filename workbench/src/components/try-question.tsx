import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { ArrowUpIcon, BookmarkPlusIcon, ChevronDownIcon } from "lucide-react"

import { CitationRow } from "@/components/answer-review"
import { AnswerText } from "@/components/answer-text"
import { CaseEditor, type Opened } from "@/components/golden-data"
import { Section, Tile } from "@/components/section"
import { SourcePanel } from "@/components/source-panel"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import { Progress } from "@/components/ui/progress"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { api, type Budget, type CitationView, type Tried } from "@/lib/api"
import { useWide } from "@/lib/hooks"
import { plural } from "@/lib/words"

function dollars(value: number | null | undefined): string {
  if (value == null) return "–"
  return value >= 0.01 || value === 0 ? `$${value.toFixed(2)}` : `$${value.toFixed(4)}`
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

/** Ask the team's agent a question within the day's limit, read the answer with its citations
 * checked, and keep it as a case (decision 0052). */
export function TryQuestion({ locked }: { locked: boolean }) {
  const wide = useWide()
  const [budget, setBudget] = useState<Budget | null>(null)
  const [question, setQuestion] = useState("")
  const [asking, setAsking] = useState(false)
  const [tried, setTried] = useState<Tried | null>(null)
  const [opened, setOpened] = useState<CitationView | null>(null)
  const [suites, setSuites] = useState<string[]>([])
  const [tasks, setTasks] = useState<string[]>([])
  const [second, setSecond] = useState(false)
  const [saving, setSaving] = useState<Opened | null>(null)

  const load = useCallback(async () => {
    const [found, golden] = await Promise.all([api.budget(), api.golden()])
    setBudget(found)
    setSuites(golden.suites.map((s) => s.suite_id))
    setTasks(golden.tasks)
    setSecond(golden.second_approval)
  }, [])

  useEffect(() => {
    load().catch((error) => toast.error(message(error)))
  }, [load])

  async function ask() {
    if (!question.trim() || asking || !budget?.can_ask) return
    setAsking(true)
    setTried(null)
    setOpened(null)
    try {
      const answered = await api.tryQuestion(question)
      setTried(answered)
      setBudget(answered.budget)
    } catch (error) {
      toast.error(message(error))
      load().catch(() => {})
    } finally {
      setAsking(false)
    }
  }

  if (!budget) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-24" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  const used = budget.limit ? Math.min(100, (budget.spent_today / budget.limit) * 100) : 0

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Try a question</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Ask {budget.target ? <span className="font-medium text-foreground">{budget.target}</span> : "the team's agent"}{" "}
          a question as your agent's users would ask it.
          {budget.checks_citations
            ? " Every citation in the answer is checked against the corpus."
            : " Citations are not checked: the engineer has not configured a judge and a corpus."}
        </p>
      </div>
      <Card className="py-3">
        <CardContent className="grid grid-cols-2 gap-2 px-3 sm:grid-cols-3">
          <Tile label="Today's limit" value={dollars(budget.limit)} caption="Set in casebench.yaml" />
          <Tile label="Spent today" value={dollars(budget.spent_today)} caption="The agent's and the judge's calls" />
          <div className="flex min-w-0 flex-col gap-2 rounded-lg bg-muted/50 p-3 max-sm:col-span-2">
            <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Left today</div>
            <div className="text-base font-semibold tracking-tight sm:text-lg">{dollars(budget.remaining)}</div>
            <Progress value={used} aria-label="Spent of today's limit" />
          </div>
        </CardContent>
      </Card>
      {!budget.can_ask && budget.why_not && (
        <Alert>
          <AlertTitle>Nothing will be sent</AlertTitle>
          <AlertDescription>{budget.why_not.charAt(0).toUpperCase() + budget.why_not.slice(1)}.</AlertDescription>
        </Alert>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          ask()
        }}
        className="relative rounded-xl border bg-card shadow-xs focus-within:ring-[3px] focus-within:ring-ring/30"
      >
        <label htmlFor="try-question" className="sr-only">
          Your question
        </label>
        <Textarea
          id="try-question"
          value={question}
          disabled={!budget.can_ask}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              ask()
            }
          }}
          placeholder="For example: can an employer dismiss a worker by WhatsApp message?"
          className="min-h-28 resize-none border-0 bg-transparent px-4 pt-4 pb-14 shadow-none focus-visible:ring-0"
        />
        <div className="absolute inset-x-3 bottom-3 flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            The cost is counted against today's limit.
          </span>
          <Button type="submit" size="sm" disabled={!question.trim() || asking || !budget.can_ask}>
            {asking ? <Spinner /> : <ArrowUpIcon />}
            Ask
            <KbdGroup className="hidden md:inline-flex">
              <Kbd className="bg-primary-foreground/15 text-primary-foreground">⌘</Kbd>
              <Kbd className="bg-primary-foreground/15 text-primary-foreground">Enter</Kbd>
            </KbdGroup>
          </Button>
        </div>
      </form>
      {asking && (
        <Section title="The answer" description="Waiting for the agent, then checking its citations">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        </Section>
      )}
      {tried && (
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
          <Section
            title="The answer"
            description={`This question cost ${dollars(tried.cost)}: the agent ${dollars(tried.agent_cost)}, the judge ${dollars(tried.judge_cost)}`}
            action={
              !locked && suites.length > 0 ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <BookmarkPlusIcon /> Save as case <ChevronDownIcon />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Add to the suite</DropdownMenuLabel>
                    {suites.map((suite) => (
                      <DropdownMenuItem
                        key={suite}
                        onSelect={() =>
                          setSaving({ suite, caseId: null, task: "qa", prefill: { question: tried.question } })
                        }
                      >
                        {suite}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : undefined
            }
          >
            <div className="flex flex-col gap-4">
              {tried.answer ? (
                <AnswerText text={tried.answer} citations={tried.citations} onOpen={setOpened} />
              ) : (
                <p className="text-sm text-muted-foreground">The agent gave no answer{tried.error ? `: ${tried.error}` : "."}</p>
              )}
              {tried.unpriced.length > 0 && (
                <Alert>
                  <AlertTitle>Part of the cost is unknown</AlertTitle>
                  <AlertDescription>
                    The agent called {tried.unpriced.join(", ")}, which has no price in casebench.yaml.
                    No more questions are sent until it has one.
                  </AlertDescription>
                </Alert>
              )}
              {tried.citations.length > 0 && (
                <ul className="-mx-2 flex flex-col" aria-label="Citations">
                  {tried.citations.map((citation) => (
                    <CitationRow
                      key={citation.citation}
                      citation={citation}
                      open={opened?.citation === citation.citation}
                      onOpen={() => setOpened(citation)}
                    />
                  ))}
                </ul>
              )}
              {tried.citations.length === 0 && budget.checks_citations && tried.answer && (
                <p className="text-sm text-muted-foreground">The answer cites no authority.</p>
              )}
            </div>
          </Section>
          {wide && opened && (
            <Section title="Source" description={`${plural(tried.citations.length, "citation")} checked`}>
              <SourcePanel citation={opened} />
            </Section>
          )}
        </div>
      )}
      {!wide && (
        <Sheet open={opened !== null} onOpenChange={(open) => !open && setOpened(null)}>
          <SheetContent data-scroll side="bottom" className="max-h-[85svh] overflow-y-auto rounded-t-xl">
            <SheetHeader>
              <SheetTitle>Source</SheetTitle>
            </SheetHeader>
            <div className="px-4 pb-6">{opened && <SourcePanel citation={opened} />}</div>
          </SheetContent>
        </Sheet>
      )}
      <CaseEditor
        opened={saving}
        tasks={tasks}
        locked={locked}
        second={second}
        onClose={() => setSaving(null)}
        onSaved={() => setSaving(null)}
      />
    </div>
  )
}

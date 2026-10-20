// Home on an engineer's own machine: each part of the setup, whether it is done, the button that
// does it, then the first run and the review queue (decision 0065).

import { useEffect, useState } from "react"
import {
  ArrowRightIcon,
  BotIcon,
  CircleCheckIcon,
  CircleDashedIcon,
  CircleAlertIcon,
  EarthIcon,
  GavelIcon,
  InboxIcon,
  KeyRoundIcon,
  MessageCircleQuestionIcon,
  PlayIcon,
  SparklesIcon,
  StethoscopeIcon,
} from "lucide-react"

import type { Page } from "@/components/app-sidebar"
import { HowItWorks } from "@/components/how-it-works"
import { Section } from "@/components/section"
import { TestResult } from "@/components/setup/test-result"
import { Button } from "@/components/ui/button"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { api, type CheckView, type Me } from "@/lib/api"
import { flag, jurisdictionName } from "@/lib/jurisdictions"
import { progress } from "@/lib/setup-progress"
import { message, useSettings } from "@/lib/use-settings"
import { cn } from "@/lib/utils"

type Tone = "done" | "todo" | "warn"

const MARKS: Record<Tone, { icon: React.ElementType; className: string; label: string }> = {
  done: { icon: CircleCheckIcon, className: "text-success", label: "Done" },
  todo: { icon: CircleDashedIcon, className: "text-muted-foreground", label: "To do" },
  warn: { icon: CircleAlertIcon, className: "text-warning", label: "Needs attention" },
}

function Step({
  icon: Icon,
  title,
  tone,
  children,
  action,
}: {
  icon: React.ElementType
  title: string
  tone: Tone
  children: React.ReactNode
  action: React.ReactNode
}) {
  const mark = MARKS[tone]
  return (
    <Item role="listitem" aria-label={title} variant="outline">
      <ItemMedia variant="icon">
        <Icon />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>
          {title}
          <mark.icon aria-label={mark.label} className={cn("size-4", mark.className)} />
        </ItemTitle>
        <ItemDescription>{children}</ItemDescription>
      </ItemContent>
      <ItemActions>{action}</ItemActions>
    </Item>
  )
}

export function HomePage({
  me,
  toReview,
  onPage,
  onGuide,
}: {
  me: Me
  toReview: number
  onPage: (page: Page) => void
  onGuide: () => void
}) {
  const { view } = useSettings()
  const [runs, setRuns] = useState<number | null>(null)
  const [checks, setChecks] = useState<CheckView[] | null>(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    api
      .runs()
      .then((found) => setRuns(found.length))
      .catch(() => setRuns(0))
  }, [])

  async function check() {
    setChecking(true)
    try {
      setChecks(await api.check())
    } catch (error) {
      setChecks([{ part: "setup", status: "failed", passed: false, reason: message(error), next: "" }])
    } finally {
      setChecking(false)
    }
  }

  if (!view) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-40" />
        <Skeleton className="h-80" />
      </div>
    )
  }
  const state = progress(view)
  const first = me.name.split(/\s+/)[0]
  const go = (page: Page) => (
    <Button variant="outline" size="sm" onClick={() => onPage(page)}>
      Open <ArrowRightIcon />
    </Button>
  )

  return (
    <div className="flex flex-col gap-6 pb-10">
      <section className="rounded-xl border bg-brand-soft p-6 md:p-8">
        <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="flex max-w-2xl flex-col gap-2">
            <h1 className="font-serif text-3xl font-medium tracking-tight md:text-4xl">Welcome, {first}</h1>
            <p className="text-muted-foreground">
              {state.complete
                ? "Casebench is set up. Run your agent on a suite, then review its answers with your lawyers."
                : "A few parts to set up, then Casebench can measure your agent against court decisions. Each is a few clicks, and saved to casebench.yaml."}
            </p>
          </div>
          <div className="flex min-w-56 flex-col gap-2">
            <div className="flex items-baseline justify-between text-sm">
              <span className="font-medium">Setup</span>
              <span className="text-muted-foreground tabular-nums">
                {state.done} of {state.total} done
              </span>
            </div>
            <Progress value={(state.done / state.total) * 100} aria-label="Setup progress" />
            {!state.complete && (
              <Button className="mt-1" onClick={onGuide}>
                <SparklesIcon /> Continue the setup guide
              </Button>
            )}
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Section title="Your setup" description="What Casebench needs, and what is done.">
          <ItemGroup role="list" className="gap-2">
            <Step
              icon={BotIcon}
              title="Your agent"
              tone={state.agent ? "done" : "todo"}
              action={
                <Button variant={state.agent ? "outline" : "default"} size="sm" onClick={onGuide}>
                  {state.agent ? "Change" : "Connect"} <ArrowRightIcon />
                </Button>
              }
            >
              {state.agent ? <code className="text-xs">{state.agent}</code> : "The AI being measured. Not connected yet."}
            </Step>
            <Step
              icon={EarthIcon}
              title="Jurisdictions"
              tone={Object.keys(state.corpora).length ? "done" : "todo"}
              action={go("jurisdictions")}
            >
              {state.jurisdictions.length || state.everywhere.length ? (
                <span className="flex flex-wrap gap-x-3 gap-y-1">
                  {state.jurisdictions.map((code) => (
                    <span key={code}>
                      <span aria-hidden>{flag(code)}</span> {jurisdictionName(code)}
                    </span>
                  ))}
                  {state.everywhere.length > 0 && <span>Every jurisdiction</span>}
                </span>
              ) : (
                "Where citations are checked. No source yet."
              )}
            </Step>
            <Step icon={GavelIcon} title="The judge" tone={state.judge ? "done" : "todo"} action={go("models")}>
              {state.judge ? (
                <>
                  <code className="text-xs">{state.judge.model}</code>
                  {state.secondJudge ? (
                    <>
                      {" "}
                      and <code className="text-xs">{state.secondJudge.model}</code>
                    </>
                  ) : null}
                </>
              ) : (
                "The model that checks citations and criteria. Not chosen yet."
              )}
            </Step>
            <Step
              icon={KeyRoundIcon}
              title="Keys"
              tone={state.missingKeys.length ? "warn" : "done"}
              action={go("models")}
            >
              {state.missingKeys.length
                ? `${state.missingKeys.map((k) => k.name).join(", ")} not set on this machine`
                : view.keys.length
                  ? "Every key the setup names is set"
                  : "No key needed yet"}
            </Step>
            <Step
              icon={StethoscopeIcon}
              title="Check"
              tone={checks ? (checks.every((c) => c.passed) ? "done" : "warn") : "todo"}
              action={
                <Button variant="outline" size="sm" onClick={check} disabled={checking || !view.exists}>
                  {checking && <Spinner />} Check now
                </Button>
              }
            >
              Calls the agent, each source and each model once, and says what to fix.
            </Step>
          </ItemGroup>
          {checks && (
            <div className="mt-4 flex flex-col gap-2">
              {checks.map((item) => (
                <TestResult key={item.part} tested={{ ...item, reason: `${item.part}: ${item.reason}` }} />
              ))}
            </div>
          )}
        </Section>

        <Section title="Next" description="Once the setup is done.">
          <div className="flex flex-col gap-2">
            {[
              {
                icon: PlayIcon,
                title: "Run an evaluation",
                text: runs ? `${runs} ${runs === 1 ? "run" : "runs"} so far` : "Builds a first suite from your sources",
                page: "run" as Page,
              },
              {
                icon: InboxIcon,
                title: "Review answers",
                text: toReview ? `${toReview} waiting for a lawyer` : "Nothing waiting",
                page: "queue" as Page,
              },
              {
                icon: MessageCircleQuestionIcon,
                title: "Try a question",
                text: "Ask your agent one question and see every citation checked",
                page: "try" as Page,
              },
            ].map((next) => (
              <Item key={next.title} variant="outline" asChild>
                <button type="button" onClick={() => onPage(next.page)}>
                  <ItemMedia variant="icon">
                    <next.icon />
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{next.title}</ItemTitle>
                    <ItemDescription>{next.text}</ItemDescription>
                  </ItemContent>
                  <ArrowRightIcon className="size-4 text-muted-foreground" />
                </button>
              </Item>
            ))}
          </div>
        </Section>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-muted-foreground">How Casebench works</h2>
        <HowItWorks />
      </section>
    </div>
  )
}

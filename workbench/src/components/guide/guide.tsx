// The setup guide a first-time engineer sees: what Casebench does, then the agent, its
// jurisdictions, the judge and a check, each saved to casebench.yaml as it is done (0065).

import { useEffect, useRef, useState } from "react"
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckIcon,
  FileCogIcon,
  LockKeyholeIcon,
  PlayIcon,
  StethoscopeIcon,
  TimerIcon,
} from "lucide-react"

import type { Page } from "@/components/app-sidebar"
import { Brand } from "@/components/brand"
import { AgentStep } from "@/components/guide/agent-step"
import { HowItWorks } from "@/components/how-it-works"
import { JurisdictionList } from "@/components/jurisdictions-page"
import { JudgeRoles } from "@/components/models-page"
import { TestResult } from "@/components/setup/test-result"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { api, type CheckView } from "@/lib/api"
import { progress, type Target } from "@/lib/setup-progress"
import { message, useSettings } from "@/lib/use-settings"
import { cn } from "@/lib/utils"

const STEPS = [
  { id: "welcome", title: "Welcome", text: "What Casebench does" },
  { id: "agent", title: "Your agent", text: "The AI being measured" },
  { id: "jurisdictions", title: "Jurisdictions", text: "Where citations are checked" },
  { id: "judge", title: "The judge", text: "The model that checks" },
  { id: "check", title: "Check", text: "Everything answers" },
] as const

type StepId = (typeof STEPS)[number]["id"]

const PROMISES = [
  { icon: TimerIcon, text: "About five minutes. Every step can be skipped and done later." },
  { icon: FileCogIcon, text: "Each choice is saved to casebench.yaml, which the command line and CI read." },
  {
    icon: LockKeyholeIcon,
    text: "Nothing leaves this machine except calls to your agent, your sources and the judge you choose.",
  },
]

function complete(target: Target | null): boolean {
  if (!target?.type) return false
  if (target.type === "python") return /\S+:\S+/.test(target.entry ?? "")
  if (target.type === "http") return Boolean(target.url && target.answer)
  if (target.type === "command") return Boolean(target.run?.includes("{question}"))
  return true
}

export function Guide({ name, onDone }: { name: string; onDone: (page?: Page) => void }) {
  const settings = useSettings()
  const { view, save } = settings
  const [step, setStep] = useState<StepId>("welcome")
  const [target, setTarget] = useState<Target | null>(null)
  const [checks, setChecks] = useState<CheckView[] | null>(null)
  const [busy, setBusy] = useState(false)
  const resumed = useRef(false)
  const index = STEPS.findIndex((s) => s.id === step)

  useEffect(() => {
    // Opened again later, the guide resumes at the first part not yet set up.
    if (!view || resumed.current) return
    resumed.current = true
    if (!view.exists) return
    const found = progress(view)
    setStep(!found.agent ? "agent" : !Object.keys(found.corpora).length ? "jurisdictions" : !found.judge ? "judge" : "check")
  }, [view])
  const state = view ? progress(view) : null
  const saved = (view?.sections.target as Target | undefined) ?? null
  const draft = target ?? saved

  const done: Record<StepId, boolean> = {
    welcome: index > 0,
    agent: Boolean(state?.agent),
    jurisdictions: Boolean(state && Object.keys(state.corpora).length),
    judge: Boolean(state?.judge),
    check: Boolean(checks?.every((c) => c.passed)),
  }

  async function next() {
    if (step === "agent" && draft && complete(draft) && JSON.stringify(draft) !== JSON.stringify(saved)) {
      setBusy(true)
      const ok = await save("target", draft)
      setBusy(false)
      if (!ok) return
    }
    setStep(STEPS[Math.min(index + 1, STEPS.length - 1)].id)
  }

  async function check() {
    setBusy(true)
    try {
      setChecks(await api.check())
    } catch (error) {
      setChecks([{ part: "setup", status: "failed", passed: false, reason: message(error), next: "" }])
    } finally {
      setBusy(false)
    }
  }

  const current = STEPS[index]
  return (
    <div className="grid min-h-svh lg:grid-cols-[22rem_minmax(0,1fr)]">
      <aside className="relative hidden flex-col gap-10 overflow-hidden bg-gradient-to-b from-primary to-primary/85 p-8 text-primary-foreground lg:flex">
        <div aria-hidden className="pointer-events-none absolute -bottom-32 -left-24 size-96 rounded-full bg-white/10 blur-3xl" />
        <Brand caption="Setup guide" light />
        <ol aria-label="Setup steps" className="relative flex flex-col gap-1">
          {STEPS.map((item, n) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => setStep(item.id)}
                aria-current={item.id === step ? "step" : undefined}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition hover:bg-white/10",
                  item.id === step && "bg-white/15",
                )}
              >
                <span
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold tabular-nums",
                    done[item.id] ? "border-transparent bg-white text-primary" : "border-white/40",
                  )}
                >
                  {done[item.id] ? <CheckIcon className="size-4" /> : n + 1}
                </span>
                <span className="flex flex-col leading-tight">
                  <span className="text-sm font-medium">{item.title}</span>
                  <span className="text-xs text-white/70">{item.text}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
        <p className="relative mt-auto text-xs text-white/70">
          Leave at any time: what you saved stays, and Home shows what is left.
        </p>
      </aside>

      <main className="flex flex-col">
        <header className="flex items-center justify-between gap-3 border-b px-5 py-3 lg:border-b-0 lg:px-10 lg:pt-6">
          <div className="lg:hidden">
            <Brand caption="Setup guide" />
          </div>
          <span className="hidden text-sm text-muted-foreground lg:block">
            Step {index + 1} of {STEPS.length}
          </span>
          <Button variant="ghost" size="sm" onClick={() => onDone()}>
            Skip the guide
          </Button>
        </header>
        <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-5 py-8 lg:px-10">
          <div className="flex flex-col gap-2">
            <h1 className="font-serif text-3xl font-medium tracking-tight md:text-4xl">
              {step === "welcome" ? `Let's set up Casebench, ${name.split(/\s+/)[0]}` : current.title}
            </h1>
            <p className="max-w-2xl text-muted-foreground">
              {step === "welcome" &&
                "Casebench measures how accurately your AI answers legal questions, against real court decisions and your lawyers' own answers."}
              {step === "agent" &&
                "How Casebench reaches the AI you are measuring. It sends each question exactly as your users would."}
              {step === "jurisdictions" &&
                "The countries your agent answers about, and where their court decisions and statutes are. Each citation in an answer is looked up there."}
              {step === "judge" &&
                "A model from the public catalog that reads each answer, finds its citations in your sources and checks what they say. Pick one from a different family than your agent's models."}
              {step === "check" &&
                "One call to your agent, each source and the judge, to see that each answers from this machine."}
            </p>
          </div>

          {step === "welcome" && (
            <div className="flex flex-col gap-6">
              <HowItWorks compact />
              <ul className="flex flex-col gap-3">
                {PROMISES.map((promise) => (
                  <li key={promise.text} className="flex items-center gap-3 text-sm">
                    <promise.icon className="size-4 shrink-0 text-primary" /> {promise.text}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {step === "agent" && <AgentStep target={draft} onChange={setTarget} />}
          {step === "jurisdictions" && <JurisdictionList settings={settings} />}
          {step === "judge" && (
            <div className="flex flex-col gap-3">
              <JudgeRoles settings={settings} second={false} />
              <p className="text-sm text-muted-foreground">
                A second judge and the models that turn court decisions into cases are on the Models page.
              </p>
            </div>
          )}
          {step === "check" && (
            <div className="flex flex-col gap-4">
              <div>
                <Button onClick={check} disabled={busy || !view?.exists}>
                  {busy ? <Spinner /> : <StethoscopeIcon />} Check the setup
                </Button>
              </div>
              {!view?.exists && (
                <p className="text-sm text-muted-foreground">Nothing is saved yet: connect your agent first.</p>
              )}
              {checks?.map((item) => (
                <TestResult key={item.part} tested={{ ...item, reason: `${item.part}: ${item.reason}` }} />
              ))}
              {checks && (
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button onClick={() => onDone("run")}>
                    <PlayIcon /> Run a first evaluation
                  </Button>
                  <Button variant="outline" onClick={() => onDone("home")}>
                    Go to Home
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
        <footer className="sticky bottom-0 border-t bg-background/90 backdrop-blur">
          <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 px-5 py-3 lg:px-10">
            <Button variant="ghost" onClick={() => setStep(STEPS[Math.max(index - 1, 0)].id)} disabled={index === 0}>
              <ArrowLeftIcon /> Back
            </Button>
            {step !== "check" ? (
              <Button
                onClick={next}
                disabled={busy || (step === "agent" && draft !== null && !complete(draft))}
              >
                {busy && <Spinner />}
                {step === "welcome" ? "Start" : done[step] || (step === "agent" && complete(draft)) ? "Continue" : "Skip for now"}
                <ArrowRightIcon />
              </Button>
            ) : (
              <Button variant="outline" onClick={() => onDone("home")}>
                Finish
              </Button>
            )}
          </div>
        </footer>
      </main>
      {settings.asking}
    </div>
  )
}

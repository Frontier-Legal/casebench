import { useState } from "react"
import {
  BookOpenCheckIcon,
  CodeIcon,
  KeyboardIcon,
  ScaleIcon,
  ShieldCheckIcon,
} from "lucide-react"

import { Brand } from "@/components/brand"
import { Button } from "@/components/ui/button"
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
  FieldTitle,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Spinner } from "@/components/ui/spinner"
import type { View } from "@/lib/api"

const POINTS = [
  {
    icon: BookOpenCheckIcon,
    title: "Evidence beside every answer",
    text: "Each citation is checked against the corpus and opens its source passage.",
  },
  {
    icon: KeyboardIcon,
    title: "One key per verdict",
    text: "The judge's suggestion is filled in. Confirm it, or overrule it with a note.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Your decision always wins",
    text: "Every verdict and approval is recorded with your name and your reason.",
  },
]

/** The first screen: who you are, and whether you review answers or build the system. With
 * nothing set up yet, building is the likelier answer, and the guide follows (0065). */
export function Welcome({
  roleLocked,
  settingUp = false,
  onStart,
}: {
  roleLocked: boolean
  settingUp?: boolean
  onStart: (name: string, view: View) => Promise<void>
}) {
  const [name, setName] = useState("")
  const [view, setView] = useState<View>(settingUp && !roleLocked ? "engineering" : "review")
  const [busy, setBusy] = useState(false)

  async function start(event: React.FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      await onStart(name.trim(), roleLocked ? "review" : view)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary via-primary to-primary/80 p-10 text-primary-foreground lg:flex">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-40 -right-40 size-[32rem] rounded-full bg-white/10 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-48 -left-32 size-[28rem] rounded-full bg-white/8 blur-3xl"
        />
        <div className="relative">
          <Brand light />
        </div>
        <div className="relative flex max-w-md flex-col gap-8">
          <h1 className="font-serif text-4xl leading-tight font-medium">
            Measure the legal accuracy of your AI, with the lawyers who know the answer.
          </h1>
          <ul className="flex flex-col gap-5">
            {POINTS.map((point) => (
              <li key={point.title} className="flex gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-white/12">
                  <point.icon className="size-4" />
                </div>
                <div>
                  <div className="font-medium">{point.title}</div>
                  <div className="text-sm text-primary-foreground/75">{point.text}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-primary-foreground/70">
          Runs on this machine. Nothing you do here leaves it.
        </p>
      </aside>
      <main className="flex items-center justify-center p-6 sm:p-10">
        <form onSubmit={start} className="flex w-full max-w-sm flex-col gap-8">
          <div className="flex flex-col gap-2">
            <div className="mb-4 lg:hidden">
              <Brand />
            </div>
            <h2 className="font-serif text-3xl font-medium tracking-tight">
              {settingUp ? "Welcome to Casebench" : "Open the review queue"}
            </h2>
            <p className="text-sm text-muted-foreground">
              {settingUp
                ? "Nothing is set up here yet. Tell us who you are, and a short guide connects your agent, its jurisdictions and a judge."
                : "Check the AI's answers against the evidence and approve cases drawn from court decisions."}
            </p>
          </div>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="name">Your name</FieldLabel>
              <Input
                id="name"
                autoFocus
                autoComplete="name"
                className="h-11"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Ayşe Yılmaz"
              />
              <FieldDescription>Your verdicts are recorded under it.</FieldDescription>
            </Field>
            {!roleLocked && (
              <FieldSet>
                <FieldLegend variant="label">What do you do?</FieldLegend>
                <RadioGroup value={view} onValueChange={(value) => setView(value as View)}>
                  <FieldLabel htmlFor="view-review">
                    <Field orientation="horizontal">
                      <ScaleIcon className="size-4 text-muted-foreground" />
                      <FieldContent>
                        <FieldTitle>I review legal answers</FieldTitle>
                        <FieldDescription>Legal text, citations and sources only.</FieldDescription>
                      </FieldContent>
                      <RadioGroupItem value="review" id="view-review" />
                    </Field>
                  </FieldLabel>
                  <FieldLabel htmlFor="view-engineering">
                    <Field orientation="horizontal">
                      <CodeIcon className="size-4 text-muted-foreground" />
                      <FieldContent>
                        <FieldTitle>I build or run the AI system</FieldTitle>
                        <FieldDescription>Also the agent's steps, tokens and raw records.</FieldDescription>
                      </FieldContent>
                      <RadioGroupItem value="engineering" id="view-engineering" />
                    </Field>
                  </FieldLabel>
                </RadioGroup>
              </FieldSet>
            )}
            <Button type="submit" size="lg" className="h-11" disabled={!name.trim() || busy}>
              {busy && <Spinner />}
              Start
            </Button>
          </FieldGroup>
        </form>
      </main>
    </div>
  )
}

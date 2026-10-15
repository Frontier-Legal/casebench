import { useMemo, useRef, useState } from "react"
import { CheckIcon, PencilIcon, XIcon } from "lucide-react"

import { Choices } from "@/components/choices"
import { EngineeringCard } from "@/components/engineering-card"
import { FinishBar, ReadOnlyBar } from "@/components/finish-bar"
import { InputsCard } from "@/components/inputs-card"
import { Passage } from "@/components/passage"
import { Overline, Section, Status } from "@/components/section"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import type { DraftItem, FactChoice, FactView, GivenFact } from "@/lib/api"
import { useAutosave, useWide } from "@/lib/hooks"
import { useShortcuts } from "@/lib/keys"
import { cn } from "@/lib/utils"
import { factKind, plural } from "@/lib/words"

interface Decided {
  decision: FactChoice | null
  value: string
  reason: string
}

const CHOICES = [
  { value: "approve" as const, label: "Approve", icon: CheckIcon },
  { value: "edit" as const, label: "Edit", icon: PencilIcon },
  { value: "reject" as const, label: "Reject", icon: XIcon },
]

function initial(item: DraftItem): Record<string, Decided> {
  const saved = (item.draft?.facts ?? {}) as Record<string, Decided>
  return Object.fromEntries(
    item.facts.map((f) => [f.id, saved[f.id] ?? { decision: null, value: f.value, reason: "" }]),
  )
}

function problem(fact: FactView, decided: Decided): string | null {
  if (!decided.decision) return "Approve, edit or reject this fact."
  if (decided.decision !== "edit") return null
  if (!decided.value.trim()) return "Write the fact as it should read."
  if (!decided.reason.trim()) return "Say why you changed it."
  if (decided.value.trim() === fact.value) return "The fact is unchanged; approve it instead."
  return null
}

/** Each fact of a court draft beside its passage in the decision; approve, edit or reject each
 * with one key, and an edit asks for a reason (decision 0050). */
export function DraftReview({
  item,
  left,
  onDraft,
  onFinish,
  onHelp,
  busy,
  readOnly = false,
}: {
  item: DraftItem
  left: number
  onDraft: (payload: Record<string, unknown>) => void
  onFinish: (facts: GivenFact[]) => void
  onHelp: () => void
  busy: boolean
  readOnly?: boolean
}) {
  const wide = useWide()
  const [decided, setDecided] = useState(() => initial(item))
  const [focus, setFocus] = useState(0)
  const [shown, setShown] = useState(false)
  const [tab, setTab] = useState("facts")
  const editors = useRef<Record<string, HTMLInputElement | null>>({})
  const payload = useMemo(() => ({ facts: decided }), [decided])
  useAutosave(payload, onDraft)
  const facts = item.facts

  function choose(id: string, decision: FactChoice) {
    setDecided((now) => ({ ...now, [id]: { ...now[id], decision } }))
    if (decision === "edit") {
      window.setTimeout(() => editors.current[id]?.focus(), 0)
    } else {
      const at = facts.findIndex((f) => f.id === id)
      setFocus(Math.min(at + 1, facts.length - 1))
    }
  }

  function finish() {
    setShown(true)
    const wrong = facts.findIndex((f) => problem(f, decided[f.id]) !== null)
    if (wrong >= 0) {
      setTab("facts")
      setFocus(wrong)
      if (decided[facts[wrong].id].decision === "edit") editors.current[facts[wrong].id]?.focus()
      return
    }
    onFinish(
      facts.map((f) => {
        const d = decided[f.id]
        return d.decision === "edit"
          ? { fact_id: f.id, decision: "edit", value: d.value.trim(), reason: d.reason.trim() }
          : { fact_id: f.id, decision: d.decision as FactChoice }
      }),
    )
  }

  useShortcuts({
    choose: (n) => {
      const fact = facts[focus]
      if (fact && n <= CHOICES.length) choose(fact.id, CHOICES[n - 1].value)
    },
    move: (by) => setFocus((at) => Math.max(0, Math.min(facts.length - 1, at + by))),
    finish,
    help: onHelp,
  })

  const text = item.decision?.text ?? null
  const marks = facts.flatMap((f) => (f.highlight ? [{ id: f.id, ...f.highlight }] : []))
  const done = facts.filter((f) => decided[f.id].decision).length

  const decision = (
    <Section
      title="The decision"
      description={
        [item.decision?.court, item.decision?.date].filter(Boolean).join(" · ") ||
        item.decision?.id ||
        "No decision is linked to this draft."
      }
      data-scroll
      className="lg:sticky lg:top-20 lg:max-h-[calc(100svh-6.5rem)] lg:overflow-y-auto"
    >
      {text ? (
        <Passage text={text} marks={marks} focused={facts[focus]?.id} />
      ) : (
        <p className="text-sm text-muted-foreground">
          The full text is not available here, so each fact shows its quote instead.
        </p>
      )}
    </Section>
  )

  const list = (
    <div className="flex flex-col gap-4">
      <InputsCard inputs={item.inputs} title="The case as drafted" />
      <Section
        title="Facts drawn from the decision"
        description="Check each against its highlighted passage. An approved case joins the answer key."
        action={
          <span className="text-xs text-muted-foreground tabular-nums">
            {done} of {facts.length} decided
          </span>
        }
      >
        <div className="flex flex-col gap-2">
          {facts.map((fact, index) => {
            const d = decided[fact.id]
            const issue = shown ? problem(fact, d) : null
            return (
              <div
                key={fact.id}
                data-row={fact.id}
                data-focused={index === focus}
                onClick={() => setFocus(index)}
                className={cn(
                  "flex flex-col gap-3 rounded-lg border border-transparent bg-muted/50 p-4 transition-colors",
                  index === focus && "border-border bg-background shadow-xs ring-[3px] ring-ring/20",
                )}
              >
                <div className="flex items-center gap-2">
                  <Overline>{factKind(fact.kind)}</Overline>
                  {d.decision && (
                    <Status
                      className="ml-auto"
                      tone={d.decision === "approve" ? "good" : d.decision === "reject" ? "bad" : "warn"}
                    >
                      {d.decision === "approve" ? "Approved" : d.decision === "edit" ? "Edited" : "Rejected"}
                    </Status>
                  )}
                </div>
                <div
                  className={cn(
                    "text-sm font-medium",
                    d.decision === "reject" && "text-muted-foreground line-through",
                  )}
                >
                  {fact.value}
                </div>
                {fact.quote && !(wide && text && fact.highlight) && (
                  <div className="text-sm text-muted-foreground">“{fact.quote}”</div>
                )}
                <Choices
                  label={`Your decision on: ${fact.value}`}
                  choices={CHOICES}
                  value={d.decision}
                  onChoose={(choice) => {
                    setFocus(index)
                    choose(fact.id, choice)
                  }}
                />
                {d.decision === "edit" && (
                  <FieldGroup className="gap-4" onClick={(event) => event.stopPropagation()}>
                    <Field>
                      <FieldLabel htmlFor={`value-${fact.id}`}>The fact as it should read</FieldLabel>
                      <Input
                        id={`value-${fact.id}`}
                        className="bg-background"
                        ref={(element) => {
                          editors.current[fact.id] = element
                        }}
                        value={d.value}
                        onChange={(event) =>
                          setDecided((now) => ({
                            ...now,
                            [fact.id]: { ...now[fact.id], value: event.target.value },
                          }))
                        }
                      />
                    </Field>
                    <Field data-invalid={issue !== null}>
                      <FieldLabel htmlFor={`reason-${fact.id}`}>Why do you change it?</FieldLabel>
                      <Textarea
                        id={`reason-${fact.id}`}
                        className="bg-background"
                        value={d.reason}
                        aria-invalid={issue !== null}
                        placeholder="For example: the court relies on the first paragraph only."
                        onChange={(event) =>
                          setDecided((now) => ({
                            ...now,
                            [fact.id]: { ...now[fact.id], reason: event.target.value },
                          }))
                        }
                      />
                      {!issue && <FieldDescription>Required. It is recorded with the change.</FieldDescription>}
                    </Field>
                  </FieldGroup>
                )}
                {issue && <FieldError>{issue}</FieldError>}
              </div>
            )
          })}
        </div>
      </Section>
      {item.engineering && <EngineeringCard engineering={item.engineering} />}
    </div>
  )

  return (
    <>
      {wide ? (
        <div className="grid grid-cols-[minmax(0,6fr)_minmax(0,5fr)] items-start gap-4">
          {decision}
          {list}
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="facts">Facts</TabsTrigger>
            <TabsTrigger value="decision">Decision</TabsTrigger>
          </TabsList>
          <TabsContent value="facts">{list}</TabsContent>
          <TabsContent value="decision">{decision}</TabsContent>
        </Tabs>
      )}
      {readOnly ? (
        <ReadOnlyBar />
      ) : (
        <FinishBar
          left={left}
          busy={busy}
          onFinish={finish}
          label="Approve the case and next"
          summary={`${done} of ${plural(facts.length, "fact")} decided`}
        />
      )}
    </>
  )
}

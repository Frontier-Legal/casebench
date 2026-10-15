import { useMemo, useRef, useState } from "react"
import { CheckIcon, XIcon } from "lucide-react"

import { Choices } from "@/components/choices"
import { FinishBar, ReadOnlyBar } from "@/components/finish-bar"
import { Overline, Section } from "@/components/section"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Textarea } from "@/components/ui/textarea"
import type { ChangeItem } from "@/lib/api"
import { useAutosave } from "@/lib/hooks"
import { useShortcuts } from "@/lib/keys"
import { inputName } from "@/lib/words"

type Decision = "approve" | "reject"

const CHOICES = [
  { value: "approve" as const, label: "Approve", icon: CheckIcon },
  { value: "reject" as const, label: "Reject", icon: XIcon },
]

function label(field: string): string {
  const known = inputName(field)
  return known === field ? field.charAt(0).toUpperCase() + field.slice(1) : known
}

function Text({ value, empty }: { value: string; empty: string }) {
  return value.trim() ? (
    <div className="text-sm leading-relaxed whitespace-pre-wrap">{value}</div>
  ) : (
    <div className="text-sm text-muted-foreground italic">{empty}</div>
  )
}

/** A change to golden data as the second editor sees it: each changed field before and after,
 * who proposed it, when and why; approve with one key, or reject with a note (0052). */
export function ChangeReview({
  item,
  left,
  onDraft,
  onFinish,
  onHelp,
  busy,
  readOnly = false,
}: {
  item: ChangeItem
  left: number
  onDraft: (payload: Record<string, unknown>) => void
  onFinish: (decision: Decision, note: string | null) => void
  onHelp: () => void
  busy: boolean
  readOnly?: boolean
}) {
  const saved = item.draft as { decision?: Decision; note?: string } | null
  const [decision, setDecision] = useState<Decision | null>(saved?.decision ?? null)
  const [note, setNote] = useState(saved?.note ?? "")
  const [shown, setShown] = useState(false)
  const box = useRef<HTMLTextAreaElement>(null)
  const payload = useMemo(() => ({ decision, note }), [decision, note])
  useAutosave(payload, onDraft)
  const isNew = item.proposal.kind === "new"

  function choose(chosen: Decision) {
    setDecision(chosen)
    if (chosen === "reject") window.setTimeout(() => box.current?.focus(), 0)
  }

  function finish() {
    setShown(true)
    if (!decision) return
    if (decision === "reject" && !note.trim()) {
      box.current?.focus()
      return
    }
    onFinish(decision, note.trim() || null)
  }

  useShortcuts({
    choose: (n) => n <= CHOICES.length && choose(CHOICES[n - 1].value),
    finish,
    help: onHelp,
  })

  const missing = shown && (!decision ? "Approve or reject the change." : decision === "reject" && !note.trim() ? "Say why you reject it; its author reads it." : null)

  return (
    <>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
        <Section
          title={isNew ? "The new case" : "What changed"}
          description={
            isNew
              ? "Every field the author wrote. The case is a draft until you approve it."
              : "Each changed field, as it is now and as it would be. Nothing changes until you approve."
          }
        >
          <div className="flex flex-col gap-4">
            {item.changes.map((change) => (
              <div key={change.field} className="flex flex-col gap-2">
                <Overline>{label(change.field)}</Overline>
                {isNew ? (
                  <div className="rounded-lg bg-muted/50 p-3">
                    <Text value={change.after} empty="Empty" />
                  </div>
                ) : (
                  <div className="grid gap-2 md:grid-cols-2">
                    <div className="flex flex-col gap-1.5 rounded-lg border border-dashed p-3">
                      <span className="text-xs text-muted-foreground">Now</span>
                      <Text value={change.before} empty="Empty" />
                    </div>
                    <div className="flex flex-col gap-1.5 rounded-lg bg-muted/50 p-3">
                      <span className="text-xs text-muted-foreground">Proposed</span>
                      <Text value={change.after} empty="Empty" />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
        <div className="flex flex-col gap-4 lg:sticky lg:top-20">
          <Section title="Why" description={`Proposed by ${item.proposal.author}`}>
            <div className="text-sm leading-relaxed">
              {item.proposal.reason ?? <span className="text-muted-foreground">No reason given.</span>}
            </div>
          </Section>
          <Section
            title="Your decision"
            description="A second editor's approval puts the change into the answer key."
          >
            <div className="flex flex-col gap-4">
              <Choices label="Your decision" choices={CHOICES} value={decision} onChoose={choose} />
              <Field data-invalid={Boolean(missing)}>
                <FieldLabel htmlFor="change-note">
                  {decision === "reject" ? "Why do you reject it?" : "A note for the author"}
                </FieldLabel>
                <Textarea
                  id="change-note"
                  ref={box}
                  value={note}
                  aria-invalid={Boolean(missing)}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder={
                    decision === "reject"
                      ? "For example: the amendment only applies from 2026."
                      : "Optional"
                  }
                />
                {missing ? (
                  <FieldError>{missing}</FieldError>
                ) : (
                  <FieldDescription>
                    {decision === "reject" ? "Required when you reject." : "Optional when you approve."}
                  </FieldDescription>
                )}
              </Field>
            </div>
          </Section>
        </div>
      </div>
      {readOnly ? (
        <ReadOnlyBar />
      ) : (
        <FinishBar
          left={left}
          busy={busy}
          onFinish={finish}
          label={decision === "reject" ? "Reject and next" : "Approve and next"}
          summary={
            decision
              ? decision === "approve"
                ? "You approve the change"
                : "You reject the change"
              : `${isNew ? "A new case" : "A change"} by ${item.proposal.author}`
          }
        />
      )}
    </>
  )
}

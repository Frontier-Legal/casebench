import { useMemo, useRef, useState } from "react"
import { BookOpenIcon, CheckIcon, ChevronRightIcon, SparklesIcon, XIcon } from "lucide-react"

import { AnswerText } from "@/components/answer-text"
import { Choices } from "@/components/choices"
import { EngineeringCard } from "@/components/engineering-card"
import { HarnessView } from "@/components/harness-view"
import { FinishBar } from "@/components/finish-bar"
import { InputsCard } from "@/components/inputs-card"
import { Overline, Section, Status } from "@/components/section"
import { CitationStatus, SourcePanel } from "@/components/source-panel"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import type { AnswerItem, CitationView, CriterionView, GivenVerdict, Verdict } from "@/lib/api"
import { useAutosave, useWide } from "@/lib/hooks"
import { useShortcuts } from "@/lib/keys"
import { cn } from "@/lib/utils"
import { CITATION_LABELS, factKind, plural } from "@/lib/words"

type Chosen = Record<string, { verdict: Verdict; note: string }>

const VERDICTS = [
  { value: "pass" as const, label: "Pass", icon: CheckIcon },
  { value: "fail" as const, label: "Fail", icon: XIcon },
]

function initial(item: AnswerItem): Chosen {
  const saved = (item.draft?.verdicts ?? {}) as Chosen
  return Object.fromEntries(
    item.criteria.map((c) => [
      c.id,
      saved[c.id] ?? {
        verdict: c.lawyer?.verdict ?? c.judge,
        note: c.lawyer?.note ?? "",
      },
    ]),
  )
}

function CriterionRow({
  criterion,
  chosen,
  focused,
  missingNote,
  onFocus,
  onChoose,
  onNote,
  noteRef,
}: {
  criterion: CriterionView
  chosen: { verdict: Verdict; note: string }
  focused: boolean
  missingNote: boolean
  onFocus: () => void
  onChoose: (verdict: Verdict) => void
  onNote: (note: string) => void
  noteRef: (element: HTMLTextAreaElement | null) => void
}) {
  const overrules = chosen.verdict !== criterion.judge
  return (
    <div
      data-row={criterion.id}
      data-focused={focused}
      onClick={onFocus}
      className={cn(
        "flex flex-col gap-3 rounded-lg border border-transparent bg-muted/50 p-4 transition-colors",
        focused && "border-border bg-background shadow-xs ring-[3px] ring-ring/20",
      )}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="tabular-nums">
          {criterion.weight > 0 ? `+${criterion.weight}` : `−${Math.abs(criterion.weight)}`}{" "}
          {criterion.weight > 0 ? "must have" : "must avoid"}
        </Badge>
        {criterion.kind && <Badge variant="secondary">{factKind(criterion.kind)}</Badge>}
        {criterion.judges_disagreed && (
          <Status tone="warn" className="ml-1">
            The two judges disagreed
          </Status>
        )}
        {overrules && <Badge className="ml-auto">Overruled</Badge>}
      </div>
      <div className="text-sm leading-snug font-medium">{criterion.text}</div>
      {criterion.evidence.length > 0 && (
        <div className="text-sm text-muted-foreground">
          <span className="text-foreground">Evidence · </span>
          {criterion.evidence.join(" · ")}
        </div>
      )}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-2 text-sm text-muted-foreground">
          <SparklesIcon className="mt-0.5 size-4 shrink-0" />
          <span className="min-w-0">
            The judge suggests{" "}
            <span className="font-medium text-foreground">{criterion.judge}</span>
            {criterion.judge_quote && <>, relying on “{criterion.judge_quote}”</>}
            {criterion.judge_note && <>. {criterion.judge_note}</>}
          </span>
        </div>
        <Choices
          label={`Your verdict on: ${criterion.text}`}
          choices={VERDICTS}
          value={chosen.verdict}
          onChoose={onChoose}
        />
      </div>
      {overrules && (
        <Field data-invalid={missingNote} onClick={(event) => event.stopPropagation()}>
          <FieldLabel htmlFor={`note-${criterion.id}`}>Why do you overrule the judge?</FieldLabel>
          <Textarea
            id={`note-${criterion.id}`}
            ref={noteRef}
            value={chosen.note}
            aria-invalid={missingNote}
            className="bg-background"
            placeholder="For example: the article is cited for the wrong proposition."
            onChange={(event) => onNote(event.target.value)}
          />
          {missingNote ? (
            <FieldError>Say why before you finish.</FieldError>
          ) : (
            <FieldDescription>Required. It is recorded with your verdict.</FieldDescription>
          )}
        </Field>
      )}
      {criterion.lawyer && (
        <p className="text-xs text-muted-foreground">
          {criterion.lawyer.by} said {criterion.lawyer.verdict} before
          {criterion.lawyer.note ? `: ${criterion.lawyer.note}` : ""}
        </p>
      )}
    </div>
  )
}

export function CitationRow({
  citation,
  open,
  onOpen,
}: {
  citation: CitationView
  open: boolean
  onOpen: () => void
}) {
  return (
    <li>
      <button
        type="button"
        data-citation={citation.label}
        onClick={onOpen}
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-muted/60",
          open && "bg-muted",
        )}
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md border bg-background">
          <BookOpenIcon className="size-4 text-muted-foreground" />
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="truncate text-sm font-medium">{citation.citation}</span>
          <span className="truncate text-xs text-muted-foreground">{citation.claim}</span>
        </span>
        <CitationStatus label={citation.label} />
        <ChevronRightIcon className="size-4 text-muted-foreground" />
        <span className="sr-only">{CITATION_LABELS[citation.label].long}</span>
      </button>
    </li>
  )
}

/** Evidence beside the answer, the judge's verdict pre-filled on each criterion, one key per
 * verdict (decision 0050). */
export function AnswerReview({
  item,
  left,
  onDraft,
  onFinish,
  onHelp,
  busy,
}: {
  item: AnswerItem
  left: number
  onDraft: (payload: Record<string, unknown>) => void
  onFinish: (verdicts: GivenVerdict[]) => void
  onHelp: () => void
  busy: boolean
}) {
  const wide = useWide()
  const [chosen, setChosen] = useState<Chosen>(() => initial(item))
  const [focus, setFocus] = useState(0)
  const [missing, setMissing] = useState<string[]>([])
  const [opened, setOpened] = useState<CitationView | null>(null)
  const [tab, setTab] = useState("answer")
  const notes = useRef<Record<string, HTMLTextAreaElement | null>>({})
  const payload = useMemo(() => ({ verdicts: chosen }), [chosen])
  useAutosave(payload, onDraft)

  const criteria = item.criteria
  const changed = criteria.filter((c) => chosen[c.id].verdict !== c.judge).length

  function choose(id: string, verdict: Verdict) {
    setChosen((now) => ({ ...now, [id]: { ...now[id], verdict } }))
    const criterion = criteria.find((c) => c.id === id)
    if (criterion && verdict !== criterion.judge && !chosen[id]?.note) {
      window.setTimeout(() => notes.current[id]?.focus(), 0)
    } else {
      const at = criteria.findIndex((c) => c.id === id)
      setFocus(Math.min(at + 1, criteria.length - 1))
    }
  }

  function finish() {
    const unexplained = criteria
      .filter((c) => chosen[c.id].verdict !== c.judge && !chosen[c.id].note.trim())
      .map((c) => c.id)
    setMissing(unexplained)
    if (unexplained.length) {
      setTab("answer")
      setFocus(criteria.findIndex((c) => c.id === unexplained[0]))
      notes.current[unexplained[0]]?.focus()
      return
    }
    onFinish(
      criteria.map((c) => ({
        criterion_id: c.id,
        verdict: chosen[c.id].verdict,
        note: chosen[c.id].note.trim() || null,
      })),
    )
  }

  useShortcuts({
    choose: (n) => {
      const criterion = criteria[focus]
      if (criterion && n <= VERDICTS.length) choose(criterion.id, VERDICTS[n - 1].value)
    },
    move: (by) => setFocus((at) => Math.max(0, Math.min(criteria.length - 1, at + by))),
    finish,
    help: onHelp,
  })

  const evidence = (
    <div className="flex flex-col gap-4">
      {wide && opened && (
        <Section
          title="Source"
          description="What the corpus holds for this citation"
          action={
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setOpened(null)}
              aria-label="Close the source"
            >
              <XIcon />
            </Button>
          }
        >
          <SourcePanel citation={opened} />
        </Section>
      )}
      <InputsCard inputs={item.inputs} />
      {item.reference.length > 0 && (
        <Section title="Checked against" description="The court's findings or the lawyer's answer key">
          <ul className="flex flex-col gap-2">
            {item.reference.map((fact) => (
              <li key={fact.id} className="flex flex-col gap-1 rounded-lg bg-muted/50 p-3">
                <Overline>{factKind(fact.kind)}</Overline>
                <div className="text-sm font-medium">{fact.value}</div>
                {fact.quote && <div className="text-sm text-muted-foreground">“{fact.quote}”</div>}
                {!fact.quote && fact.note && (
                  <div className="text-sm text-muted-foreground">{fact.note}</div>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )

  const answer = (
    <div className="flex flex-col gap-4">
      <Section
        title="The AI's answer"
        description={
          item.citations.length > 0
            ? `${plural(item.citations.length, "citation")} checked against the corpus`
            : undefined
        }
      >
        <div className="flex flex-col gap-4">
          {item.answer ? (
            <AnswerText text={item.answer} citations={item.citations} onOpen={setOpened} />
          ) : (
            <p className="text-sm text-muted-foreground">The AI gave no answer.</p>
          )}
          {item.citations.length > 0 && (
            <ul className="-mx-2 flex flex-col" aria-label="Citations">
              {item.citations.map((citation) => (
                <CitationRow
                  key={citation.citation}
                  citation={citation}
                  open={opened?.citation === citation.citation}
                  onOpen={() => setOpened(citation)}
                />
              ))}
            </ul>
          )}
        </div>
      </Section>
      {criteria.length > 0 && (
        <Section
          title="Your verdict"
          description="The judge's suggestion is filled in. Keep it, or change it and say why."
          action={<span className="text-xs text-muted-foreground">Saved as you go</span>}
        >
          <div className="flex flex-col gap-2">
            {criteria.map((criterion, index) => (
              <CriterionRow
                key={criterion.id}
                criterion={criterion}
                chosen={chosen[criterion.id]}
                focused={index === focus}
                missingNote={missing.includes(criterion.id) && !chosen[criterion.id].note.trim()}
                onFocus={() => setFocus(index)}
                onChoose={(verdict) => {
                  setFocus(index)
                  choose(criterion.id, verdict)
                }}
                onNote={(note) =>
                  setChosen((now) => ({ ...now, [criterion.id]: { ...now[criterion.id], note } }))
                }
                noteRef={(element) => {
                  notes.current[criterion.id] = element
                }}
              />
            ))}
          </div>
        </Section>
      )}
      {item.engineering && <EngineeringCard engineering={item.engineering} scores={item.scores} />}
    </div>
  )

  return (
    <>
      {wide ? (
        <div className="grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-start gap-4">
          <div
            data-scroll
            className="sticky top-20 max-h-[calc(100svh-6.5rem)] overflow-y-auto p-px pb-2"
          >
            {evidence}
          </div>
          {answer}
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="answer">Answer and verdict</TabsTrigger>
            <TabsTrigger value="evidence">Evidence</TabsTrigger>
          </TabsList>
          <TabsContent value="answer" className="mt-2">
            {answer}
          </TabsContent>
          <TabsContent value="evidence" className="mt-2">
            {evidence}
          </TabsContent>
        </Tabs>
      )}
      {!wide && (
        <Sheet open={opened !== null} onOpenChange={(open) => !open && setOpened(null)}>
          <SheetContent
            data-scroll
            side="bottom"
            className="max-h-[85svh] overflow-y-auto rounded-t-xl"
          >
            <SheetHeader>
              <SheetTitle>Source</SheetTitle>
            </SheetHeader>
            <div className="px-4 pb-6">{opened && <SourcePanel citation={opened} />}</div>
          </SheetContent>
        </Sheet>
      )}
      {item.engineering && <HarnessView itemKey={item.key} />}
      <FinishBar
        left={left}
        busy={busy}
        onFinish={finish}
        summary={
          criteria.length
            ? changed
              ? `You overrule the judge on ${plural(changed, "criterion", "criteria")}`
              : "You agree with the judge on every criterion"
            : "Read the answer and its citations"
        }
      />
    </>
  )
}

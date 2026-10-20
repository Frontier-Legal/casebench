// The Jurisdictions page: each country whose law answers are checked against, the sources that
// hold its documents, a test of each, and a way to add another country (decision 0065).

import { useState } from "react"
import { EarthIcon, PlusIcon, Trash2Icon } from "lucide-react"

import { AddJurisdiction } from "@/components/jurisdictions/add-jurisdiction"
import { Status } from "@/components/section"
import { TestButton } from "@/components/setup/test-result"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { flag, jurisdictionName } from "@/lib/jurisdictions"
import { progress, sourceKind, sourcePlace, type Corpus } from "@/lib/setup-progress"
import { useSettings, type Settings } from "@/lib/use-settings"

function holdsOf(corpus: Corpus): string[] {
  return corpus.holds?.length ? corpus.holds : ["decisions", "statutes"]
}

function SourceRow({
  name,
  corpus,
  code,
  onRemove,
}: {
  name: string
  corpus: Corpus
  code: string | null
  onRemove: () => void
}) {
  const place = sourcePlace(corpus)
  return (
    <li className="flex flex-col gap-2 rounded-lg border bg-background p-3">
      <div className="flex items-start gap-2">
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="text-sm font-medium">{name}</span>
          <span className="truncate text-xs text-muted-foreground">
            {sourceKind(corpus)}
            {place ? ` · ${place}` : ""}
          </span>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          aria-label={code ? `Stop using ${name} for ${code}` : `Remove ${name}`}
        >
          <Trash2Icon />
        </Button>
      </div>
      <TestButton label="Test a search" test={() => api.testSource(corpus as Record<string, unknown>)} />
    </li>
  )
}

function JurisdictionCard({
  code,
  sources,
  onRemove,
}: {
  code: string | null
  sources: [string, Corpus][]
  onRemove: (name: string) => void
}) {
  const holds = new Set(sources.flatMap(([, corpus]) => holdsOf(corpus)))
  return (
    <article
      aria-label={code ? jurisdictionName(code) : "Every jurisdiction"}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4 shadow-xs"
    >
      <div className="flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-lg bg-brand-soft text-2xl leading-none">
          {code ? <span aria-hidden>{flag(code)}</span> : <EarthIcon className="size-5 text-primary" />}
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate font-medium">{code ? jurisdictionName(code) : "Every jurisdiction"}</span>
          <span className="text-xs text-muted-foreground">
            {code ? <span className="font-mono">{code}</span> : "Sources that name no jurisdiction"}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Status tone={holds.has("decisions") ? "good" : "warn"}>
          {holds.has("decisions") ? "Court decisions" : "No court decisions"}
        </Status>
        <Status tone={holds.has("statutes") ? "good" : "warn"}>
          {holds.has("statutes") ? "Statutes" : "No statutes"}
        </Status>
      </div>
      <ul className="flex flex-col gap-2">
        {sources.map(([name, corpus]) => (
          <SourceRow key={name} name={name} corpus={corpus} code={code} onRemove={() => onRemove(name)} />
        ))}
      </ul>
    </article>
  )
}

/** Every jurisdiction with its sources, and the button that adds one. */
export function JurisdictionList({ settings }: { settings: Settings }) {
  const { view, setView, save } = settings
  const [adding, setAdding] = useState(false)
  if (!view) return <Skeleton className="h-48" />
  const state = progress(view)
  const entries = Object.entries(state.corpora)

  function remove(code: string | null, name: string) {
    const corpus = state.corpora[name]
    const left = (corpus.jurisdictions ?? []).filter((c) => c !== code)
    const next = { ...state.corpora }
    if (code === null || left.length === 0) delete next[name]
    else next[name] = { ...corpus, jurisdictions: left }
    return save("corpora", Object.keys(next).length ? next : null)
  }

  const dialog = (
    <AddJurisdiction open={adding} onOpenChange={setAdding} view={view} onView={setView} save={save} />
  )
  if (!entries.length) {
    return (
      <>
        <Empty className="border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon" className="bg-brand-soft text-primary">
              <EarthIcon />
            </EmptyMedia>
            <EmptyTitle>No jurisdiction yet</EmptyTitle>
            <EmptyDescription>
              Add the country whose court decisions and statutes your agent cites. Until one has a source,
              Casebench grades rulings only and cannot check a citation.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button onClick={() => setAdding(true)}>
              <PlusIcon /> Add a jurisdiction
            </Button>
          </EmptyContent>
        </Empty>
        {dialog}
      </>
    )
  }
  const cards: [string | null, [string, Corpus][]][] = state.jurisdictions.map((code) => [
    code,
    entries.filter(([, corpus]) => corpus.jurisdictions?.includes(code)),
  ])
  if (state.everywhere.length) {
    cards.push([null, entries.filter(([name]) => state.everywhere.includes(name))])
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">
          {state.jurisdictions.length} {state.jurisdictions.length === 1 ? "jurisdiction" : "jurisdictions"}
        </Badge>
        <Badge variant="secondary">
          {entries.length} {entries.length === 1 ? "source" : "sources"}
        </Badge>
        <Button className="ml-auto" onClick={() => setAdding(true)}>
          <PlusIcon /> Add a jurisdiction
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {cards.map(([code, sources]) => (
          <JurisdictionCard
            key={code ?? "every"}
            code={code}
            sources={sources}
            onRemove={(name) => remove(code, name)}
          />
        ))}
      </div>
      {dialog}
    </div>
  )
}

export function JurisdictionsPage() {
  const settings = useSettings()
  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Jurisdictions</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          The countries whose law your agent's answers are checked against. Each needs a source of its court
          decisions, and of its statutes when answers cite them. A new country is a source, never code: a citation
          goes to the sources of the jurisdiction it names.
        </p>
      </div>
      <JurisdictionList settings={settings} />
      {settings.asking}
    </div>
  )
}

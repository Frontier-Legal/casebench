import { useEffect, useState } from "react"

import { Passage } from "@/components/passage"
import { Status } from "@/components/section"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type CitationView, type Document } from "@/lib/api"
import { CITATION_LABELS } from "@/lib/words"

const TONES = {
  verified: "good",
  misgrounded: "warn",
  fabricated: "bad",
  unchecked: "none",
} as const

export function CitationStatus({ label }: { label: CitationView["label"] }) {
  return (
    <Status tone={TONES[label]}>
      {CITATION_LABELS[label].short}
    </Status>
  )
}

/** One citation: what the answer said, what the corpus says, and the source passage. */
export function SourcePanel({ citation }: { citation: CitationView }) {
  const [document, setDocument] = useState<Document | null>(null)
  const [missing, setMissing] = useState(false)

  useEffect(() => {
    setDocument(null)
    setMissing(false)
    if (!citation.document_id) return
    let live = true
    api
      .document(citation.document_id, citation.quote)
      .then((found) => live && setDocument(found))
      .catch(() => live && setMissing(true))
    return () => {
      live = false
    }
  }, [citation.document_id, citation.quote])

  return (
    <div className="flex flex-col gap-4" data-testid="source-panel">
      <div className="flex flex-col gap-1.5">
        <CitationStatus label={citation.label} />
        <div className="font-medium">{citation.citation}</div>
        <p className="text-sm text-muted-foreground">{CITATION_LABELS[citation.label].long}</p>
      </div>
      <dl className="grid gap-2 rounded-lg bg-muted/50 p-3 text-sm">
        {citation.claim && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Cited for</dt>
            <dd className="text-right">{citation.claim}</dd>
          </div>
        )}
        {citation.reason && citation.label !== "verified" && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Why</dt>
            <dd className="text-right">{citation.reason}</dd>
          </div>
        )}
        {document && (
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Source</dt>
            <dd className="text-right">
              {[document.court, document.date].filter(Boolean).join(" · ") || document.id}
            </dd>
          </div>
        )}
      </dl>
      {citation.document_id && !document && !missing && <Skeleton className="h-40 w-full" />}
      {document?.text && (
        <Passage
          text={document.text}
          marks={document.highlight ? [{ id: "quote", ...document.highlight }] : []}
          focused={document.highlight ? "quote" : null}
        />
      )}
      {!document && citation.quote && (missing || !citation.document_id) && (
        <blockquote className="border-l-2 pl-4 text-sm italic">{citation.quote}</blockquote>
      )}
      {missing && (
        <p className="text-xs text-muted-foreground">
          The full text is not available here: no configured corpus holds it.
        </p>
      )}
    </div>
  )
}

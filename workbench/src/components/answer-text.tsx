import type { CitationView } from "@/lib/api"
import { CITATION_LABELS } from "@/lib/words"

interface Found {
  start: number
  end: number
  citation: CitationView
}

function placed(text: string, citations: CitationView[]): Found[] {
  const found: Found[] = []
  for (const citation of citations) {
    let from = 0
    while (from < text.length) {
      const start = text.indexOf(citation.citation, from)
      if (start < 0) break
      const end = start + citation.citation.length
      if (!found.some((f) => start < f.end && f.start < end)) found.push({ start, end, citation })
      from = end
    }
  }
  return found.sort((a, b) => a.start - b.start)
}

/** The answer with each citation marked by what the corpus says, opening its source. */
export function AnswerText({
  text,
  citations,
  onOpen,
}: {
  text: string
  citations: CitationView[]
  onOpen: (citation: CitationView) => void
}) {
  const pieces: React.ReactNode[] = []
  let at = 0
  for (const { start, end, citation } of placed(text, citations)) {
    pieces.push(text.slice(at, start))
    pieces.push(
      <mark
        key={`${start}-${citation.citation}`}
        data-tone={citation.label}
        className="cursor-pointer"
        role="button"
        tabIndex={0}
        title={CITATION_LABELS[citation.label].long}
        onClick={() => onOpen(citation)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            onOpen(citation)
          }
        }}
      >
        {text.slice(start, end)}
      </mark>,
    )
    at = end
  }
  pieces.push(text.slice(at))
  return <div className="text-[0.95rem] leading-7 whitespace-pre-wrap">{pieces}</div>
}

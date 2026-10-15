import { useEffect, useRef } from "react"

import type { Highlight } from "@/lib/api"

export interface Marked extends Highlight {
  id: string
}

// The header above and the finish bar below cover this much of the window.
const COVERED_TOP = 72
const COVERED_BOTTOM = 96

/** Scrolls the nearest panel marked `data-scroll` so the element sits in the middle of the
 * part of the panel the reader can see; with `page`, the page scrolls too when that is not
 * enough. */
function reveal(element: Element, page: boolean) {
  const panel = element.closest("[data-scroll]")
  if (panel instanceof HTMLElement && panel.scrollHeight > panel.clientHeight) {
    const box = panel.getBoundingClientRect()
    const top = Math.max(box.top, COVERED_TOP)
    const bottom = Math.min(box.bottom, window.innerHeight - COVERED_BOTTOM)
    const target = (top + bottom) / 2
    panel.scrollTop += element.getBoundingClientRect().top - target
  }
  const seen = element.getBoundingClientRect()
  if (page && seen.top < COVERED_TOP || seen.bottom > window.innerHeight - COVERED_BOTTOM) {
    element.scrollIntoView?.({ block: "center" })
  }
}

/** A document's text with its passages marked; the focused one is brought into view. */
export function Passage({
  text,
  marks,
  focused,
}: {
  text: string
  marks: Marked[]
  focused?: string | null
}) {
  const box = useRef<HTMLDivElement>(null)
  // When the item opens, only the passage's own panel scrolls; the page stays at its top.
  const opened = useRef(false)

  useEffect(() => {
    if (!focused) return
    const mark = box.current?.querySelector(`[data-mark="${CSS.escape(focused)}"]`)
    if (mark) reveal(mark, opened.current)
    opened.current = true
  }, [focused])

  const ordered = [...marks].sort((a, b) => a.start - b.start)
  const pieces: React.ReactNode[] = []
  let at = 0
  for (const mark of ordered) {
    if (mark.start < at) continue
    pieces.push(text.slice(at, mark.start))
    pieces.push(
      <mark key={mark.id} data-mark={mark.id} data-tone="passage" data-focused={mark.id === focused}>
        {text.slice(mark.start, mark.end)}
      </mark>,
    )
    at = mark.end
  }
  pieces.push(text.slice(at))

  return (
    <div ref={box} className="text-sm leading-7 whitespace-pre-wrap">
      {pieces}
    </div>
  )
}

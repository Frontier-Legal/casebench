import { ArrowRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import { Spinner } from "@/components/ui/spinner"
import { plural } from "@/lib/words"

const MAC = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform)

/** In place of the finish bar, for a caller whose role reads the item but does not act on it
 * (decision 0058). */
export function ReadOnlyBar() {
  return (
    <div className="sticky bottom-0 z-10 -mx-4 mt-2 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:-mx-6">
      <div className="px-4 py-3 text-sm text-muted-foreground md:px-6">
        Your role lets you read this item. Someone with a reviewer's or an editor's role acts on it.
      </div>
    </div>
  )
}

/** The bar at the foot of every item: what is decided, and finishing it. */
export function FinishBar({
  summary,
  left,
  busy,
  onFinish,
  label = "Finish and next",
  unit = "item",
  last = "The last item in the queue",
}: {
  summary: string
  left: number
  busy: boolean
  onFinish: () => void
  label?: string
  unit?: string
  last?: string
}) {
  return (
    <div className="sticky bottom-0 z-10 -mx-4 mt-2 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:-mx-6">
      <div className="flex items-center gap-3 px-4 py-3 md:px-6">
        <div className="min-w-0 flex-1 text-sm">
          <div className="truncate font-medium">{summary}</div>
          <div className="text-xs text-muted-foreground">
            {left > 1 ? `${plural(left - 1, `more ${unit}`)} after this one` : last}
          </div>
        </div>
        <Button onClick={onFinish} disabled={busy} size="lg" className="h-11 gap-2 px-5 md:h-10">
          {busy ? <Spinner /> : <ArrowRightIcon className="sm:hidden" />}
          <span className="hidden sm:inline">{label}</span>
          <span className="sm:hidden">Finish</span>
          <KbdGroup className="hidden md:inline-flex">
            <Kbd className="bg-primary-foreground/15 text-primary-foreground">{MAC ? "⌘" : "Ctrl"}</Kbd>
            <Kbd className="bg-primary-foreground/15 text-primary-foreground">Enter</Kbd>
          </KbdGroup>
        </Button>
      </div>
    </div>
  )
}

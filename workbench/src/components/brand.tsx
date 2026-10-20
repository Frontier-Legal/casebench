// Casebench's mark and name, the same in the sidebar, the welcome screen and the guide.

import { ScaleIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/** The scales on an ink-blue square; `light` sits on a dark or brand background. */
export function Mark({ className, light = false }: { className?: string; light?: boolean }) {
  return (
    <div
      aria-hidden
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-lg shadow-sm",
        light
          ? "bg-white/15 text-white ring-1 ring-white/20"
          : "bg-gradient-to-br from-primary to-primary/75 text-primary-foreground",
        className,
      )}
    >
      <ScaleIcon className="size-[55%]" />
    </div>
  )
}

export function Brand({ caption, light = false }: { caption?: string; light?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <Mark light={light} />
      <div className="leading-tight">
        <div className="font-semibold tracking-tight">Casebench</div>
        {caption && (
          <div className={cn("text-xs", light ? "text-white/70" : "text-muted-foreground")}>{caption}</div>
        )}
      </div>
    </div>
  )
}

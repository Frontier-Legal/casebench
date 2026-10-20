// How Casebench measures an AI system, drawn as the four parts a run passes through, in words a
// lawyer and an engineer both read (decision 0065).

import { BotIcon, GavelIcon, LandmarkIcon, UserCheckIcon } from "lucide-react"

import { cn } from "@/lib/utils"

const PARTS = [
  {
    icon: BotIcon,
    title: "Your agent answers",
    text: "Each case's question goes to the AI you are measuring, exactly as your users would ask it.",
  },
  {
    icon: LandmarkIcon,
    title: "The courts hold the answer",
    text: "Cases come from real decisions or from your lawyers. Every citation is looked up in your sources.",
  },
  {
    icon: GavelIcon,
    title: "A judge model checks",
    text: "It finds each authority the answer cites and checks that the source says what the answer claims.",
  },
  {
    icon: UserCheckIcon,
    title: "Lawyers have the last word",
    text: "They confirm or overrule the judge, one key per verdict. Their decision always counts.",
  },
]

export function HowItWorks({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <ol
      aria-label="How Casebench works"
      className={cn("grid gap-3", compact ? "sm:grid-cols-2" : "sm:grid-cols-2 xl:grid-cols-4", className)}
    >
      {PARTS.map((part, index) => (
        <li
          key={part.title}
          className="relative flex flex-col gap-3 overflow-hidden rounded-xl border bg-card p-4 shadow-xs"
        >
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-brand-soft text-primary">
              <part.icon className="size-4.5" />
            </div>
            <span className="font-mono text-xs text-muted-foreground tabular-nums">0{index + 1}</span>
          </div>
          <div className="flex flex-col gap-1">
            <div className="font-medium">{part.title}</div>
            <p className="text-sm text-muted-foreground">{part.text}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

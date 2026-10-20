// How Casebench measures an AI system, drawn as the four parts a run passes through, in words a
// lawyer and an engineer both read (decision 0065).

import { BotIcon, GavelIcon, LandmarkIcon, UserCheckIcon } from "lucide-react"

import { Item, ItemContent, ItemDescription, ItemGroup, ItemMedia, ItemTitle } from "@/components/ui/item"
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
    <ItemGroup
      role="list"
      aria-label="How Casebench works"
      className={cn("grid gap-3", compact ? "sm:grid-cols-2" : "sm:grid-cols-2 xl:grid-cols-4", className)}
    >
      {PARTS.map((part) => (
        <Item key={part.title} role="listitem" variant="outline" className="items-start">
          <ItemMedia variant="icon">
            <part.icon />
          </ItemMedia>
          <ItemContent>
            <ItemTitle>{part.title}</ItemTitle>
            <ItemDescription>{part.text}</ItemDescription>
          </ItemContent>
        </Item>
      ))}
    </ItemGroup>
  )
}

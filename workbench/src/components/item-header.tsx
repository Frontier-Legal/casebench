import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Tile } from "@/components/section"
import type { AnswerItem, ChangeItem, DraftItem, Item } from "@/lib/api"
import { plural, taskName } from "@/lib/words"

function answerTiles(item: AnswerItem) {
  const met = item.criteria.filter((c) => c.judge === "pass").length
  const counts = { verified: 0, misgrounded: 0, fabricated: 0, unchecked: 0 }
  for (const citation of item.citations) counts[citation.label] += 1
  const wrong = [
    counts.misgrounded && `${counts.misgrounded} misused`,
    counts.fabricated && `${counts.fabricated} not found`,
  ].filter(Boolean)
  const disagreed = item.criteria.filter((c) => c.judges_disagreed).length
  return (
    <>
      <Tile
        label="Judge"
        value={item.criteria.length ? `${met} of ${item.criteria.length} passed` : "No criteria"}
        caption={
          disagreed
            ? `The two judges disagreed on ${plural(disagreed, "criterion", "criteria")}`
            : "Suggestions you confirm or overrule"
        }
      />
      <Tile
        label="Citations"
        value={
          item.citations.length
            ? `${counts.verified} of ${item.citations.length} supported`
            : "None cited"
        }
        caption={wrong.length ? wrong.join(" · ") : "Checked against the corpus"}
      />
      <Tile
        label="Run"
        className="max-sm:hidden"
        value={item.where.replace(/^run /, "")}
        caption={taskName(item.task)}
      />
    </>
  )
}

function draftTiles(item: DraftItem) {
  return (
    <>
      <Tile
        label="Decision"
        value={item.decision?.court ?? item.decision?.id ?? "Not linked"}
        caption={item.decision?.date ?? undefined}
      />
      <Tile label="Facts" value={plural(item.facts.length, "fact")} caption="Approve, edit or reject each" />
      <Tile
        label="Suite"
        className="max-sm:hidden"
        value={item.where.replace(/^suite /, "")}
        caption={taskName(item.task)}
      />
    </>
  )
}

function changeTiles(item: ChangeItem) {
  const at = new Date(item.proposal.at)
  return (
    <>
      <Tile label="Author" value={item.proposal.author} caption={item.proposal.kind === "new" ? "Wrote a new case" : "Proposed a change"} />
      <Tile
        label="Proposed"
        value={at.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
        caption={at.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
      />
      <Tile
        label="Fields"
        className="max-sm:hidden"
        value={plural(item.changes.length, "field")}
        caption={item.where}
      />
    </>
  )
}

const HEADLINES: Record<Item["kind"], string> = {
  answer: "Answer to review",
  draft: "Court draft to approve",
  change: "Change to approve",
}

/** What the item is, where it comes from, and what it asks of the reader. */
export function ItemHeader({ item }: { item: Item }) {
  const answer = item.kind === "answer"
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">
            {item.kind === "change" && item.proposal.kind === "new"
              ? "New case to approve"
              : HEADLINES[item.kind]}
          </Badge>
          <Badge variant="outline">{taskName(item.task)}</Badge>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-balance md:text-2xl">{item.title}</h1>
      </div>
      <Card className="py-3">
        <CardContent className="grid grid-cols-2 gap-2 px-3 sm:grid-cols-3">
          {answer ? answerTiles(item) : item.kind === "change" ? changeTiles(item) : draftTiles(item)}
        </CardContent>
      </Card>
    </div>
  )
}

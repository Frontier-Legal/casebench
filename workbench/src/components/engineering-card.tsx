import { useState } from "react"

import { Section, Tile } from "@/components/section"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { Engineering, ScoreView } from "@/lib/api"

function number(value: number | null | undefined, unit = ""): string {
  return value == null ? "–" : `${Math.round(value).toLocaleString()}${unit}`
}

/** What only the engineering view shows: the agent's steps, tokens, latency and raw records. */
export function EngineeringCard({
  engineering,
  scores = [],
}: {
  engineering: Engineering
  scores?: ScoreView[]
}) {
  const [raw, setRaw] = useState(false)
  return (
    <Section
      title="For engineers"
      description="Scores, the agent's steps and the raw records. Reviewers do not see this."
      data-testid="engineering"
      footer={
        <Button variant="outline" size="sm" onClick={() => setRaw(!raw)}>
          {raw ? "Hide" : "Show"} the raw records
        </Button>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-2">
          <Tile label="Latency" value={number(engineering.latency_ms, " ms")} />
          <Tile label="Input tokens" value={number(engineering.input_tokens)} />
          <Tile label="Output tokens" value={number(engineering.output_tokens)} />
        </div>
        {scores.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead>Label</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scores.map((score) => (
                <TableRow key={score.metric}>
                  <TableCell className="font-mono text-xs">{score.metric}</TableCell>
                  <TableCell className="text-right tabular-nums">{score.value.toFixed(2)}</TableCell>
                  <TableCell className="text-muted-foreground">{score.label ?? "–"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {engineering.steps.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Step</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="text-right">ms</TableHead>
                <TableHead className="text-right">In</TableHead>
                <TableHead className="text-right">Out</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {engineering.steps.map((step, index) => (
                <TableRow key={index}>
                  <TableCell>{step.name ?? step.kind}</TableCell>
                  <TableCell className="font-mono text-xs">{step.model ?? "–"}</TableCell>
                  <TableCell className="text-right tabular-nums">{number(step.duration_ms)}</TableCell>
                  <TableCell className="text-right tabular-nums">{number(step.input_tokens)}</TableCell>
                  <TableCell className="text-right tabular-nums">{number(step.output_tokens)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {raw && (
          <pre className="max-h-96 overflow-auto rounded-lg bg-muted/50 p-3 font-mono text-xs">
            {JSON.stringify(engineering.raw, null, 2)}
          </pre>
        )}
      </div>
    </Section>
  )
}

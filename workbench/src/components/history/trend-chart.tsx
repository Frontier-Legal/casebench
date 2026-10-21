// One measure across a suite's runs, drawn with shadcn's chart: its value as a line, its 95%
// interval as a band, and a line at each run whose settings moved it (decision 0067).

import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import type { HistoryPoint, HistoryRun } from "@/lib/api"

export function percent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`
}

export function day(moment: string | null): string {
  if (!moment) return "unknown date"
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(new Date(moment))
}

const CONFIG = {
  mean: { label: "Value", color: "var(--primary)" },
  band: { label: "95% interval", color: "var(--primary)" },
} satisfies ChartConfig

export function TrendChart({
  label,
  runs,
  points,
  moved = [],
  changes,
}: {
  label: string
  runs: HistoryRun[]
  points: HistoryPoint[]
  moved?: string[]
  /** What changed at a run, by run id, for the tooltip. */
  changes: Record<string, string[]>
}) {
  const byRun = new Map(points.map((p) => [p.run_id, p]))
  const dates = new Map(runs.map((run) => [run.run_id, day(run.scored_at)]))
  const data = runs.map((run) => {
    const point = byRun.get(run.run_id)
    return {
      run: run.run_id,
      mean: point ? point.mean * 100 : null,
      band: point ? [point.low * 100, point.high * 100] : null,
      n: point?.n ?? null,
    }
  })
  return (
    <ChartContainer config={CONFIG} className="aspect-auto h-44 w-full" aria-label={`${label}, run by run`}>
      <ComposedChart data={data} accessibilityLayer margin={{ left: 0, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="run"
          tickLine={false}
          axisLine={false}
          minTickGap={24}
          tickFormatter={(run: string) => dates.get(run) ?? run}
        />
        <YAxis domain={[0, 100]} tickLine={false} axisLine={false} width={40} tickFormatter={(v: number) => `${v}%`} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(_, payload) => {
                const run = String(payload?.[0]?.payload?.run ?? "")
                const changed = changes[run] ?? []
                return `${dates.get(run) ?? run}${changed.length ? ` · changed: ${changed.join(", ")}` : ""}`
              }}
              formatter={(value, name, item) =>
                name === "band" || value == null
                  ? null
                  : `${percent(Number(value) / 100)} · ${percent(item.payload.band[0] / 100)} to ${percent(
                      item.payload.band[1] / 100,
                    )} · ${item.payload.n} answers`
              }
            />
          }
        />
        {moved.map((run) => (
          <ReferenceLine key={run} x={run} stroke="var(--warning)" />
        ))}
        <Area dataKey="band" stroke="none" fill="var(--color-band)" fillOpacity={0.12} isAnimationActive={false} />
        <Line
          dataKey="mean"
          stroke="var(--color-mean)"
          strokeWidth={2}
          dot={{ r: 3 }}
          connectNulls
          isAnimationActive={false}
        />
      </ComposedChart>
    </ChartContainer>
  )
}

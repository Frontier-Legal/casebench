// One measure across a suite's runs: its value as a line, its 95% interval as a band, a mark
// where settings moved it, and a crosshair that reads out the nearest run (decision 0067).

import { useId, useRef, useState } from "react"

import type { HistoryPoint, HistoryRun } from "@/lib/api"
import { cn } from "@/lib/utils"

const WIDTH = 640
const HEIGHT = 168
const PAD = { top: 14, right: 12, bottom: 22, left: 36 }

export function percent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`
}

export function day(moment: string | null): string {
  if (!moment) return "unknown date"
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short" }).format(new Date(moment))
}

function longDay(moment: string | null): string {
  if (!moment) return "unknown date"
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(moment))
}

export function TrendChart({
  label,
  runs,
  points,
  moved = [],
  changes,
  className,
}: {
  label: string
  runs: HistoryRun[]
  points: HistoryPoint[]
  moved?: string[]
  /** What changed at a run, by run id, for the readout. */
  changes: Record<string, string[]>
  className?: string
}) {
  const [at, setAt] = useState<number | null>(null)
  const box = useRef<SVGSVGElement>(null)
  const titleId = useId()
  const byRun = new Map(points.map((p) => [p.run_id, p]))
  const shown = runs.map((run) => ({ run, point: byRun.get(run.run_id) ?? null }))
  const plotW = WIDTH - PAD.left - PAD.right
  const plotH = HEIGHT - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (shown.length <= 1 ? plotW / 2 : (i / (shown.length - 1)) * plotW)
  // Scores are shares, from 0 to 1; a wider value widens the scale rather than leave the plot.
  const top = Math.max(1, ...points.map((p) => p.high))
  const bottom = Math.min(0, ...points.map((p) => p.low))
  const y = (v: number) => PAD.top + (1 - (v - bottom) / (top - bottom || 1)) * plotH
  const present = shown.flatMap(({ point }, i) => (point ? [{ i, point }] : []))
  const line = present.map(({ i, point }, k) => `${k ? "L" : "M"}${x(i)},${y(point.mean)}`).join(" ")
  const band =
    present.length > 1
      ? `M${present.map(({ i, point }) => `${x(i)},${y(point.high)}`).join(" L")} L${[...present]
          .reverse()
          .map(({ i, point }) => `${x(i)},${y(point.low)}`)
          .join(" L")} Z`
      : ""
  const ticks = [0, 0.25, 0.5, 0.75, 1].filter((t) => t >= bottom && t <= top)
  const labelled = shown.length <= 8 ? shown.map((_, i) => i) : [0, Math.floor((shown.length - 1) / 2), shown.length - 1]

  function nearest(clientX: number) {
    const rect = box.current?.getBoundingClientRect()
    if (!rect || !shown.length) return
    const fromLeft = ((clientX - rect.left) / rect.width) * WIDTH
    let best = 0
    shown.forEach((_, i) => {
      if (Math.abs(x(i) - fromLeft) < Math.abs(x(best) - fromLeft)) best = i
    })
    setAt(best)
  }

  const hovered = at !== null ? shown[at] : null
  return (
    <div className={cn("relative", className)}>
      <svg
        ref={box}
        role="img"
        aria-labelledby={titleId}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full touch-none overflow-visible outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        tabIndex={0}
        onPointerMove={(event) => nearest(event.clientX)}
        onPointerLeave={() => setAt(null)}
        onFocus={() => setAt(shown.length - 1)}
        onBlur={() => setAt(null)}
        onKeyDown={(event) => {
          if (event.key === "ArrowLeft") setAt(Math.max(0, (at ?? shown.length) - 1))
          if (event.key === "ArrowRight") setAt(Math.min(shown.length - 1, (at ?? -1) + 1))
        }}
      >
        <title id={titleId}>{label}, run by run, with its 95% interval</title>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeWidth={1} />
            <text x={PAD.left - 6} y={y(t)} dy="0.32em" textAnchor="end" className="fill-muted-foreground text-[10px]">
              {Math.round(t * 100)}%
            </text>
          </g>
        ))}
        {shown.map(({ run }, i) =>
          moved.includes(run.run_id) ? (
            <g key={`moved-${run.run_id}`}>
              <line x1={x(i)} x2={x(i)} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="var(--warning)" strokeWidth={1} />
              <rect x={x(i) - 3} y={PAD.top - 7} width={6} height={6} transform={`rotate(45 ${x(i)} ${PAD.top - 4})`} fill="var(--warning)" />
            </g>
          ) : null,
        )}
        {band && <path d={band} fill="var(--primary)" fillOpacity={0.1} />}
        {line && <path d={line} fill="none" stroke="var(--primary)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />}
        {present.map(({ i, point }) => (
          <circle
            key={point.run_id}
            cx={x(i)}
            cy={y(point.mean)}
            r={at === i ? 5 : 4}
            fill="var(--primary)"
            stroke="var(--card)"
            strokeWidth={2}
          />
        ))}
        {labelled.map((i) => (
          <text
            key={`x-${i}`}
            x={x(i)}
            y={HEIGHT - 6}
            textAnchor={shown.length > 1 && i === shown.length - 1 ? "end" : i === 0 && shown.length > 1 ? "start" : "middle"}
            className="fill-muted-foreground text-[10px]"
          >
            {day(shown[i].run.scored_at)}
          </text>
        ))}
        {at !== null && (
          <line x1={x(at)} x2={x(at)} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="var(--muted-foreground)" strokeOpacity={0.5} strokeWidth={1} />
        )}
      </svg>
      {hovered && at !== null && (
        <div
          role="status"
          className="pointer-events-none absolute top-0 z-10 w-56 rounded-lg border bg-popover p-2.5 text-xs text-popover-foreground shadow-md"
          style={{
            left: `${(x(at) / WIDTH) * 100}%`,
            transform: x(at) > WIDTH / 2 ? "translateX(calc(-100% - 8px))" : "translateX(8px)",
          }}
        >
          <div className="font-medium">{longDay(hovered.run.scored_at)}</div>
          <div className="truncate font-mono text-[11px] text-muted-foreground">{hovered.run.run_id}</div>
          {hovered.point ? (
            <div className="mt-1.5">
              <span className="text-sm font-semibold tabular-nums">{percent(hovered.point.mean)}</span>{" "}
              <span className="text-muted-foreground tabular-nums">
                {percent(hovered.point.low)} to {percent(hovered.point.high)} · {hovered.point.n} answers
              </span>
            </div>
          ) : (
            <div className="mt-1.5 text-muted-foreground">Not measured in this run</div>
          )}
          {(changes[hovered.run.run_id] ?? []).length > 0 && (
            <div className="mt-1.5 text-muted-foreground">Changed: {changes[hovered.run.run_id].join(", ")}</div>
          )}
        </div>
      )}
    </div>
  )
}

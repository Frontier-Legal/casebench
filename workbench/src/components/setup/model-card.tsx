// One model Casebench calls, as a card: what it is, what it costs, its key, a test, and the
// buttons that change or remove it (decision 0065).

import { useState } from "react"
import { RefreshCwIcon, Trash2Icon } from "lucide-react"

import { Status } from "@/components/section"
import { CatalogDialog, type ModelBlock } from "@/components/settings/model-editor"
import { SetKey } from "@/components/settings/sections"
import { TestButton } from "@/components/setup/test-result"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api, type KeyView, type ModelView, type SettingsView } from "@/lib/api"

function price(input: number | null | undefined, output: number | null | undefined): string {
  if (input == null && output == null) return "No price set"
  return `$${input ?? "?"} in · $${output ?? "?"} out per million tokens`
}

function initials(provider: string): string {
  return provider.slice(0, 2).toUpperCase()
}

/** The key a model reads, whether this machine has it, and a way to set it. */
export function KeyLine({
  name,
  keys,
  onView,
}: {
  name: string | null
  keys: KeyView[]
  onView: (view: SettingsView) => void
}) {
  if (!name) return <span className="text-xs text-muted-foreground">Uses this machine's own credentials</span>
  const where = keys.find((k) => k.name === name)?.where ?? "missing"
  return (
    <div className="flex flex-wrap items-center gap-2">
      {where === "missing" ? (
        <Status tone="bad">{name} is not set</Status>
      ) : (
        <Status tone="good">{name} is set</Status>
      )}
      <SetKey name={name} onSet={onView} label={where === "missing" ? "Set key" : "Replace key"} />
    </div>
  )
}

export function ModelCard({
  title,
  view,
  model,
  block,
  onView,
  onChange,
  onRemove,
}: {
  title: string
  view: SettingsView
  model: ModelView
  block: ModelBlock
  onView: (view: SettingsView) => void
  onChange: (block: ModelBlock) => void
  onRemove?: () => void
}) {
  const [picking, setPicking] = useState(false)
  return (
    <article aria-label={title} className="flex flex-col gap-4 rounded-xl border bg-card p-4 shadow-xs">
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-brand-soft font-mono text-xs font-semibold text-primary">
          {initials(model.provider)}
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="truncate font-mono text-sm font-medium">{model.model}</span>
            {model.family && <Badge variant="secondary">{model.family} family</Badge>}
          </div>
          <span className="text-xs text-muted-foreground">
            {model.provider} · {price(model.price_input, model.price_output)}
            {model.context_window ? ` · ${model.context_window.toLocaleString("en")} token window` : ""}
          </span>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button variant="outline" size="sm" onClick={() => setPicking(true)}>
            <RefreshCwIcon /> Change
          </Button>
          {onRemove && (
            <Button variant="ghost" size="sm" onClick={onRemove} aria-label={`Remove ${title.toLowerCase()}`}>
              <Trash2Icon />
            </Button>
          )}
        </div>
      </div>
      <KeyLine name={model.key} keys={view.keys} onView={onView} />
      <TestButton label="Test this model" test={() => api.testModel(block as Record<string, unknown>)} />
      <CatalogDialog
        open={picking}
        onOpenChange={setPicking}
        onPicked={(picked) => {
          setPicking(false)
          onChange({ ...picked, candidates: block.candidates })
        }}
      />
    </article>
  )
}

/** A role with no model yet: what it would do, and the button that picks one. */
export function EmptyRole({
  title,
  text,
  action,
  onPicked,
}: {
  title: string
  text: string
  action: string
  onPicked: (block: ModelBlock) => void
}) {
  const [picking, setPicking] = useState(false)
  return (
    <div
      aria-label={title}
      className="flex flex-col items-start gap-3 rounded-xl border border-dashed bg-muted/30 p-4 sm:flex-row sm:items-center"
    >
      <p className="flex-1 text-sm text-muted-foreground">{text}</p>
      <Button variant="outline" onClick={() => setPicking(true)}>
        {action}
      </Button>
      <CatalogDialog
        open={picking}
        onOpenChange={setPicking}
        onPicked={(picked) => {
          setPicking(false)
          onPicked(picked)
        }}
      />
    </div>
  )
}

// One model Casebench calls itself, a judge or an extraction model, edited field by field or
// picked from the public model catalog as init picks one (decisions 0032, 0063).

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { BookOpenIcon, SearchIcon } from "lucide-react"

import { ChoiceField, NumberField, OptionsField, TextField } from "@/components/settings/fields"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import { api, type CatalogModel, type CatalogProvider } from "@/lib/api"
import { cn } from "@/lib/utils"

export type ModelBlock = {
  provider?: string
  model?: string
  options?: Record<string, unknown>
  provider_source?: string | null
  candidates?: number | null
  context_window?: number | null
  price?: { input: number; output: number } | null
}

// The options a provider commonly takes, offered with one click (decision 0038).
const OPTION_NAMES = [
  "base_url",
  "api_key_env",
  "max_tokens",
  "family",
  "reasoning_effort",
  "thinking_budget",
  "temperature",
]

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function dollars(value: number | null): string {
  return value == null ? "–" : `$${value}`
}

export function ModelEditor({
  block,
  onChange,
  providers,
  judge,
}: {
  block: ModelBlock
  onChange: (block: ModelBlock) => void
  providers: string[]
  /** A judge also says how many search results it may match a citation against. */
  judge: boolean
}) {
  const [picking, setPicking] = useState(false)
  const price = block.price ?? null
  function setPrice(side: "input" | "output", value: number | null) {
    const next = { input: price?.input ?? null, output: price?.output ?? null, [side]: value }
    onChange({
      ...block,
      price: next.input == null && next.output == null ? null : (next as { input: number; output: number }),
    })
  }
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" size="sm" onClick={() => setPicking(true)}>
          <BookOpenIcon /> Pick from the model catalog
        </Button>
        <span className="text-xs text-muted-foreground">
          Fills in the provider, its options, the context window and the price.
        </span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <ChoiceField
          label="Provider"
          description="The installed plugin that speaks the model's API."
          value={block.provider}
          choices={providers.map((p) => ({ value: p, label: p }))}
          onChange={(provider) => onChange({ ...block, provider })}
        />
        <TextField
          label="Model"
          description="The id the provider knows the model by."
          value={block.model}
          onChange={(model) => onChange({ ...block, model: model ?? undefined })}
        />
        <NumberField
          label="Price per million input tokens (USD)"
          value={price?.input}
          min={0}
          onChange={(value) => setPrice("input", value)}
        />
        <NumberField
          label="Price per million output tokens (USD)"
          value={price?.output}
          min={0}
          onChange={(value) => setPrice("output", value)}
        />
        <NumberField
          label="Context window (tokens)"
          description="A matching call is split only when it would not fit."
          value={block.context_window}
          step="1"
          min={1}
          onChange={(context_window) => onChange({ ...block, context_window })}
        />
        {judge && (
          <NumberField
            label="Search results per citation"
            description="How many documents the judge may match one citation against."
            value={block.candidates ?? 5}
            step="1"
            min={1}
            onChange={(candidates) => onChange({ ...block, candidates })}
          />
        )}
      </div>
      <OptionsField
        label="Options"
        description="Passed to the provider: its address, the variable its key is read from, its output limit and model settings. A key is named here, never written."
        value={block.options ?? {}}
        suggestions={OPTION_NAMES}
        onChange={(options) => onChange({ ...block, options })}
      />
      <CatalogDialog
        open={picking}
        onOpenChange={setPicking}
        onPicked={(picked) => {
          onChange({ ...picked, candidates: block.candidates })
          setPicking(false)
        }}
      />
    </div>
  )
}

export function CatalogDialog({
  open,
  onOpenChange,
  onPicked,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onPicked: (block: ModelBlock) => void
}) {
  const [providers, setProviders] = useState<CatalogProvider[] | null>(null)
  const [provider, setProvider] = useState<string | null>(null)
  const [models, setModels] = useState<CatalogModel[] | null>(null)
  const [search, setSearch] = useState("")
  const [model, setModel] = useState<string | null>(null)
  const [plugins, setPlugins] = useState<string[]>([])
  const [plugin, setPlugin] = useState<string | null>(null)
  const [missing, setMissing] = useState<Record<string, string>>({})
  const [block, setBlock] = useState<ModelBlock | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open || providers) return
    api.catalog().then(setProviders).catch((error) => {
      toast.error(message(error))
      onOpenChange(false)
    })
  }, [open, providers, onOpenChange])

  useEffect(() => {
    setModels(null)
    setModel(null)
    setBlock(null)
    if (!provider) return
    api.catalogModels(provider).then(setModels).catch((error) => toast.error(message(error)))
  }, [provider])

  const shownModels = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return (models ?? []).filter(
      (m) => !needle || m.name.toLowerCase().includes(needle) || m.id.toLowerCase().includes(needle),
    )
  }, [models, search])

  async function pick(chosen: string, through: string | null) {
    if (!provider) return
    setModel(chosen)
    setBusy(true)
    try {
      const picked = await api.pickModel(provider, chosen, through)
      setPlugins(picked.plugins)
      setBlock(picked.block as ModelBlock | null)
      setMissing(Object.fromEntries(picked.missing.map((name) => [name, ""])))
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }

  const ready = block !== null && Object.values(missing).every((v) => v.trim())

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Pick a model from the catalog</DialogTitle>
          <DialogDescription>
            The public model catalog lists each provider's models with their price and limits.
          </DialogDescription>
        </DialogHeader>
        {!providers ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Loading the model catalog: every provider's models, prices and limits.
          </p>
        ) : (
          <ChoiceField
            label="Provider"
            value={provider}
            choices={providers.map((p) => ({ value: p.id, label: `${p.name} (${p.models})` }))}
            onChange={setProvider}
            placeholder="Choose a provider"
          />
        )}
        {provider && (
          <div className="flex flex-col gap-2">
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
              <Input
                aria-label="Find a model"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Find a model"
                className="pl-8"
              />
            </div>
            <ul aria-label="Models" className="max-h-64 overflow-y-auto rounded-lg border">
              {models === null ? (
                <li className="p-3">
                  <Skeleton className="h-6" />
                </li>
              ) : (
                shownModels.map((m) => (
                  <li key={m.id}>
                    <button
                      type="button"
                      onClick={() => pick(m.id, null)}
                      aria-pressed={model === m.id}
                      className={cn(
                        "flex w-full items-center justify-between gap-3 border-b px-3 py-2 text-left text-sm last:border-b-0 hover:bg-muted/60",
                        model === m.id && "bg-primary/8",
                      )}
                    >
                      <span className="min-w-0">
                        <span className="block truncate font-medium">{m.name}</span>
                        <span className="block truncate font-mono text-xs text-muted-foreground">
                          {m.id}
                          {m.family ? ` · ${m.family}` : ""}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                        {dollars(m.price_input)} / {dollars(m.price_output)}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
            <p className="text-xs text-muted-foreground">Prices are per million input / output tokens.</p>
          </div>
        )}
        {plugins.length > 0 && model && (
          <ChoiceField
            label="Which installed plugin speaks this provider's API?"
            value={plugin}
            choices={plugins.map((p) => ({ value: p, label: p }))}
            onChange={(chosen) => {
              setPlugin(chosen)
              pick(model, chosen)
            }}
          />
        )}
        {Object.keys(missing).map((name) => (
          <TextField
            key={name}
            label={`The provider's ${name.replace("_", " ")}`}
            description="The catalog does not list it."
            value={missing[name]}
            onChange={(value) => setMissing({ ...missing, [name]: value ?? "" })}
          />
        ))}
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!ready || busy}
            onClick={() =>
              block && onPicked({ ...block, options: { ...(block.options ?? {}), ...missing } })
            }
          >
            {busy && <Spinner />} Use this model
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// Add a jurisdiction in three choices: the country, where its documents are, and the details of
// that source, tested before it is saved to casebench.yaml (decision 0065).

import { useState } from "react"
import { toast } from "sonner"
import {
  ArrowLeftIcon,
  BadgeCheckIcon,
  FlaskConicalIcon,
  GlobeIcon,
  LinkIcon,
  PlugIcon,
  PuzzleIcon,
} from "lucide-react"

import { ApiSource } from "@/components/jurisdictions/api-source"
import { CountryPicker } from "@/components/jurisdictions/country-picker"
import type { Found } from "@/components/jurisdictions/field-picker"
import { McpSource } from "@/components/jurisdictions/mcp-source"
import { ProfileSource } from "@/components/jurisdictions/profile-source"
import { PickField, TextField } from "@/components/settings/fields"
import { ChoiceCards } from "@/components/setup/choice-cards"
import { TestButton } from "@/components/setup/test-result"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Spinner } from "@/components/ui/spinner"
import { api, type SettingsView } from "@/lib/api"
import { flag, jurisdictionName } from "@/lib/jurisdictions"
import { progress, sourceKind, sourcePlace, type Corpus } from "@/lib/setup-progress"

type How = "api" | "mcp" | "profile" | "existing" | "folder" | "other"

// In the order sources usually come: a data provider's or the firm's own API first, a folder
// only to try Casebench on a few documents.
const HOWS: { value: How; icon: React.ElementType; title: string; text: string }[] = [
  {
    value: "api",
    icon: GlobeIcon,
    title: "A document API",
    text: "A legal data provider's API, or your firm's own search service.",
  },
  {
    value: "mcp",
    icon: PlugIcon,
    title: "An MCP server",
    text: "A server with a search tool and a document tool, hosted or started here.",
  },
  {
    value: "profile",
    icon: BadgeCheckIcon,
    title: "A provider's profile",
    text: "A ready description of a provider's API: only its key to set.",
  },
  {
    value: "existing",
    icon: LinkIcon,
    title: "A source already connected",
    text: "One that also holds this jurisdiction's documents.",
  },
  {
    value: "folder",
    icon: FlaskConicalIcon,
    title: "A folder of sample documents",
    text: "One JSON file per document, to try Casebench before connecting a real source.",
  },
  {
    value: "other",
    icon: PuzzleIcon,
    title: "A plugin",
    text: "A connector package someone wrote for a source none of these reach.",
  },
]

const HOLDS = [
  { value: "decisions", label: "Court decisions" },
  { value: "statutes", label: "Statutes" },
]

/** A name casebench.yaml takes, no other source has: lowercase words joined by hyphens. */
export function freeName(wanted: string, taken: string[]): string {
  const base = wanted.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "corpus"
  let name = base
  for (let n = 2; taken.includes(name); n++) name = `${base}-${n}`
  return name
}

export function AddJurisdiction({
  open,
  onOpenChange,
  view,
  onView,
  save,
  preset,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  view: SettingsView
  onView: (view: SettingsView) => void
  save: (section: string, value: unknown) => Promise<boolean>
  preset?: string | null
}) {
  const state = progress(view)
  const [code, setCode] = useState<string | null>(preset ?? null)
  const [step, setStep] = useState<"country" | "how" | "details">(preset ? "how" : "country")
  const [how, setHow] = useState<How | null>(null)
  const [path, setPath] = useState("")
  const [probe, setProbe] = useState("")
  const [holds, setHolds] = useState<string[]>([])
  const [existing, setExisting] = useState<string | null>(null)
  const [fromSource, setFromSource] = useState<Found>(null)
  const [busy, setBusy] = useState(false)
  const taken = Object.keys(state.corpora)

  function reset() {
    setCode(preset ?? null)
    setStep(preset ? "how" : "country")
    setHow(null)
    setPath("")
    setProbe("")
    setHolds([])
    setExisting(null)
    setFromSource(null)
  }

  const named = code ? jurisdictionName(code) : ""
  const folderBlock: Corpus = {
    connector: "folder",
    jurisdictions: code ? [code] : [],
    ...(holds.length ? { holds } : {}),
    options: { path: path.trim() },
    ...(probe.trim() ? { probe: probe.trim() } : {}),
  }

  function added(): { name: string; block: Corpus } | null {
    if (!code) return null
    if (how === "folder" && path.trim()) {
      return { name: freeName(`${code}-documents`, taken), block: folderBlock }
    }
    if ((how === "api" || how === "mcp" || how === "profile") && fromSource) {
      const block = { ...fromSource.block, ...(holds.length ? { holds } : {}) } as Corpus
      return { name: freeName(fromSource.name, taken), block }
    }
    if (how === "existing" && existing) {
      const corpus = state.corpora[existing]
      const codes = [...new Set([...(corpus.jurisdictions ?? []), code])]
      return { name: existing, block: { ...corpus, jurisdictions: codes } }
    }
    return null
  }

  async function finish() {
    const found = added()
    if (!found) return
    setBusy(true)
    try {
      if (await save("corpora", { ...state.corpora, [found.name]: found.block })) {
        toast.success(`${named} added: citations are checked against ${found.name}`)
        onOpenChange(false)
        reset()
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next)
        if (!next) reset()
      }}
    >
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {step === "country" ? (
              "Add a jurisdiction"
            ) : (
              <span className="flex items-center gap-2">
                <span aria-hidden>{code && flag(code)}</span> {named}
              </span>
            )}
          </DialogTitle>
          <DialogDescription>
            {step === "country"
              ? "The country whose court decisions and statutes your agent's answers cite."
              : step === "how"
                ? "Where Casebench reads its documents, to check each citation an answer makes."
                : "Tell Casebench where the documents are, then test that a search finds one."}
          </DialogDescription>
        </DialogHeader>
        {step === "country" && (
          <CountryPicker
            value={code}
            covered={state.jurisdictions}
            onChange={(picked) => {
              setCode(picked)
              setStep("how")
            }}
          />
        )}
        {step === "how" && (
          <ChoiceCards
            label="Where its documents are"
            className="sm:grid-cols-2"
            value={how}
            onChange={(chosen) => {
              setHow(chosen as How)
              setStep("details")
            }}
            choices={HOWS.filter((h) => h.value !== "existing" || taken.length > 0).map((h) => ({
              value: h.value,
              icon: h.icon,
              title: h.title,
              text: h.text,
            }))}
          />
        )}
        {step === "details" && how === "folder" && (
          <div className="flex flex-col gap-4">
            <TextField
              label="Folder"
              description="Relative to this project, or a full path. Each .json file is one document: its id, jurisdiction, court, date and text."
              placeholder={`${(code ?? "xx").toLowerCase()}-decisions`}
              value={path}
              onChange={(value) => setPath(value ?? "")}
            />
            <TextField
              label="A search that finds a document"
              description="Optional: words one of its documents contains; checks run it too."
              value={probe}
              onChange={(value) => setProbe(value ?? "")}
            />
            <PickField label="What it holds" description="Both when none is ticked." options={HOLDS} values={holds} onChange={setHolds} />
            <TestButton
              label="Test this folder"
              disabled={!path.trim()}
              test={() => api.testSource(folderBlock, probe.trim() || null)}
            />
          </div>
        )}
        {step === "details" && (how === "api" || how === "mcp" || how === "profile") && code && (
          <div className="flex flex-col gap-4">
            {how === "api" && <ApiSource view={view} onView={onView} jurisdiction={code} onReady={setFromSource} />}
            {how === "mcp" && <McpSource jurisdiction={code} onReady={setFromSource} />}
            {how === "profile" && (
              <ProfileSource view={view} onView={onView} jurisdiction={code} onReady={setFromSource} />
            )}
            <PickField label="What it holds" description="Both when none is ticked." options={HOLDS} values={holds} onChange={setHolds} />
          </div>
        )}
        {step === "details" && how === "existing" && (
          <div className="flex flex-col gap-2">
            <ChoiceCards
              label="Sources connected"
              value={existing}
              onChange={setExisting}
              choices={Object.entries(state.corpora).map(([name, corpus]) => ({
                value: name,
                title: name,
                text: `${sourceKind(corpus)}${sourcePlace(corpus) ? ` · ${sourcePlace(corpus)}` : ""} · ${
                  corpus.jurisdictions?.length ? corpus.jurisdictions.join(", ") : "every jurisdiction"
                }`,
              }))}
            />
            {existing && !state.corpora[existing].jurisdictions?.length && (
              <p className="text-sm text-muted-foreground">
                It covers every jurisdiction now; naming {named} makes it cover {named} only.
              </p>
            )}
          </div>
        )}
        {step === "details" && how === "other" && (
          <div className="flex flex-col gap-2 text-sm">
            <p>
              A connector plugin is a Python package. Once it is installed in this project, add the source in
              Settings, under Corpus, with the plugin as its connector and {named} as its jurisdiction.
            </p>
            <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs">{`casebench plugin new connector --name my-source`}</pre>
            <p className="text-muted-foreground">That writes a plugin to start from, with its conformance test.</p>
          </div>
        )}
        <DialogFooter className="sm:justify-between">
          {step !== "country" ? (
            <Button
              variant="ghost"
              onClick={() => setStep(step === "details" ? "how" : preset ? "how" : "country")}
              disabled={step === "how" && Boolean(preset)}
            >
              <ArrowLeftIcon /> Back
            </Button>
          ) : (
            <span />
          )}
          {step === "details" && how !== "other" && (
            <Button onClick={finish} disabled={!added() || busy}>
              {busy && <Spinner />} Add {named}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// One search, its first result's fields picked by a person from their values, then one
// document fetched and its fields suggested: shared by a document API and an MCP server (0065).

import { useState } from "react"
import { CircleAlertIcon, FileSearchIcon, SearchIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { ChoiceField } from "@/components/settings/fields"
import { Spinner } from "@/components/ui/spinner"
import type { Connected, Leaf, Picks } from "@/lib/api"
import { message } from "@/lib/use-settings"

const RESULT_FIELDS = [
  { name: "id", label: "The document's id (needed)" },
  { name: "citation", label: "How the source cites it" },
  { name: "type", label: "What kind of document it is" },
  { name: "passage", label: "The passage the search matched" },
]
const DOCUMENT_FIELDS = [
  { name: "id", label: "Id" },
  { name: "text", label: "Full text" },
  { name: "date", label: "Date" },
  { name: "court", label: "Court" },
  { name: "jurisdiction", label: "Jurisdiction" },
  { name: "level", label: "Court level" },
]
// A field a response does not hold; no JSONPath is written so.
const NONE = "none"

export type Found = { name: string; block: Record<string, unknown> } | null

function FieldPick({
  label,
  choices,
  value,
  onChange,
  hint,
}: {
  label: string
  choices: Leaf[]
  value: string
  onChange: (path: string) => void
  hint?: string
}) {
  const shown = (text: string) => (text.length > 60 ? `${text.slice(0, 59)}…` : text)
  return (
    <ChoiceField
      label={label}
      description={hint}
      value={value || NONE}
      choices={[
        { value: NONE, label: "Not in it" },
        ...choices.map((leaf) => ({ value: leaf.path, label: `${shown(leaf.value)} — ${leaf.path}` })),
      ]}
      onChange={(path) => onChange(path === NONE ? "" : path)}
    />
  )
}

const only = (map: Record<string, string>) => Object.fromEntries(Object.entries(map).filter(([, v]) => v))

/** `connect` sends what is picked so far; `ready` says the address and search are filled in. */
export function FieldPicker({
  ready,
  connect,
  onReady,
}: {
  ready: boolean
  connect: (picks: Pick<Picks, "result_fields" | "fields">) => Promise<Connected>
  onReady: (found: Found) => void
}) {
  const [resultFields, setResultFields] = useState<Record<string, string>>({})
  const [fields, setFields] = useState<Record<string, string>>({})
  const [found, setFound] = useState<Connected | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function look(picked: Record<string, string>, documentFields: Record<string, string>) {
    setBusy(true)
    setError(null)
    try {
      const shown = await connect({ result_fields: picked, fields: documentFields })
      setFound(shown)
      setFields(shown.fields)
      onReady(shown.block ? { name: shown.name, block: shown.block } : null)
    } catch (caught) {
      setError(message(caught))
      onReady(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <Button type="button" onClick={() => look({}, {})} disabled={!ready || busy}>
          {busy && !found ? <Spinner /> : <SearchIcon />} Search the source
        </Button>
      </div>
      {error && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>The source did not answer as expected</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {found && found.result_choices.length > 0 && (
        <section aria-label="A search result" className="flex flex-col gap-4 rounded-lg border p-4">
          <div>
            <div className="text-sm font-medium">What a search result says</div>
            <p className="text-sm text-muted-foreground">
              The first result of your search, field by field. Pick where each part is; the judge reads the
              citation, type and passage to match an answer's citations.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {RESULT_FIELDS.map((field) => (
              <FieldPick
                key={field.name}
                label={field.label}
                choices={found.result_choices}
                value={resultFields[field.name] ?? ""}
                onChange={(path) => setResultFields({ ...resultFields, [field.name]: path })}
              />
            ))}
          </div>
          <div>
            <Button
              type="button"
              variant={found.block ? "outline" : "default"}
              onClick={() => look(only(resultFields), {})}
              disabled={!resultFields.id || busy}
            >
              {busy ? <Spinner /> : <FileSearchIcon />} Fetch that document
            </Button>
          </div>
        </section>
      )}
      {found?.block && (
        <section aria-label="The document" className="flex flex-col gap-4 rounded-lg border p-4">
          <div>
            <div className="text-sm font-medium">What a document says</div>
            <p className="text-sm text-muted-foreground">
              Suggested from the values in the document fetched. Correct any that are wrong.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {DOCUMENT_FIELDS.map((field) => (
              <FieldPick
                key={field.name}
                label={field.label}
                choices={found.document_choices}
                value={fields[field.name] ?? ""}
                hint={found.missing.includes(field.name) ? "Not found yet: checks will name it." : undefined}
                onChange={(path) => {
                  const next = only({ ...fields, [field.name]: path })
                  setFields(next)
                  look(only(resultFields), next)
                }}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

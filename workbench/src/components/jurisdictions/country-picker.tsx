// Pick a jurisdiction by its name: every code casebench.yaml takes, found by name or code, and a
// part of a country typed as ISO 3166-2 (decision 0065).

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { CheckIcon, SearchIcon } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { byName, flag, jurisdictionName } from "@/lib/jurisdictions"
import { message } from "@/lib/use-settings"
import { cn } from "@/lib/utils"

// ISO 3166-2: a country's code, a hyphen, and up to three letters or digits.
const PART = /^[A-Z]{2}-[A-Z0-9]{1,3}$/

export function CountryPicker({
  value,
  onChange,
  covered = [],
}: {
  value: string | null
  onChange: (code: string) => void
  /** Codes that already have a source, marked so a person sees what is done. */
  covered?: string[]
}) {
  const [codes, setCodes] = useState<string[] | null>(null)
  const [search, setSearch] = useState("")

  useEffect(() => {
    api
      .jurisdictionCodes()
      .then((found) => setCodes(byName(found)))
      .catch((error) => toast.error(message(error)))
  }, [])

  const typed = search.trim().toUpperCase()
  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase()
    const found = (codes ?? []).filter(
      (code) => !needle || code.toLowerCase() === needle || jurisdictionName(code).toLowerCase().includes(needle),
    )
    const part = PART.test(typed) && codes?.includes(typed.slice(0, 2)) ? [typed] : []
    return [...part, ...found]
  }, [codes, search, typed])

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <SearchIcon className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted-foreground" />
        <Input
          aria-label="Find a country"
          autoFocus
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="France, Türkiye, US-CA…"
          className="pl-8"
        />
      </div>
      <ul aria-label="Jurisdictions" className="max-h-72 overflow-y-auto rounded-lg border">
        {codes === null ? (
          <li className="p-3">
            <Skeleton className="h-6" />
          </li>
        ) : shown.length === 0 ? (
          <li className="p-3 text-sm text-muted-foreground">
            No country by that name. A part of a country is written like US-CA.
          </li>
        ) : (
          shown.map((code) => (
            <li key={code}>
              <button
                type="button"
                onClick={() => onChange(code)}
                aria-pressed={value === code}
                className={cn(
                  "flex w-full items-center gap-3 border-b px-3 py-2 text-left text-sm last:border-b-0 hover:bg-muted/60",
                  value === code && "bg-accent text-accent-foreground",
                )}
              >
                <span aria-hidden className="w-6 text-lg leading-none">
                  {flag(code)}
                </span>
                <span className="flex-1 truncate">{jurisdictionName(code)}</span>
                {covered.includes(code) && <span className="text-xs text-muted-foreground">has a source</span>}
                <span className="font-mono text-xs text-muted-foreground">{code}</span>
                {value === code && <CheckIcon className="size-4 text-primary" />}
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  )
}

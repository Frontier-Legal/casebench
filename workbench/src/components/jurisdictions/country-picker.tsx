// Pick a jurisdiction by its name: every code casebench.yaml takes, found by name or code, and a
// part of a country typed as ISO 3166-2 (decision 0065).

import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { CheckIcon } from "lucide-react"

import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command"
import { Spinner } from "@/components/ui/spinner"
import { api } from "@/lib/api"
import { byName, flag, jurisdictionName } from "@/lib/jurisdictions"
import { message } from "@/lib/use-settings"

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

  const named = useMemo(() => (codes ?? []).map((code) => ({ code, name: jurisdictionName(code) })), [codes])
  const typed = search.trim().toUpperCase()
  const part = PART.test(typed) && codes?.includes(typed.slice(0, 2)) ? typed : null

  return (
    <Command label="Find a country" className="rounded-lg border">
      <CommandInput
        aria-label="Find a country"
        placeholder="France, Türkiye, US-CA…"
        value={search}
        onValueChange={setSearch}
        autoFocus
      />
      <CommandList>
        {codes === null ? (
          <div className="flex items-center gap-2 p-3 text-sm text-muted-foreground">
            <Spinner /> Loading the countries
          </div>
        ) : (
          <>
            <CommandEmpty>No country by that name. A part of a country is written like US-CA.</CommandEmpty>
            <CommandGroup>
              {part && (
                <CommandItem value={part} onSelect={() => onChange(part)}>
                  <span aria-hidden>{flag(part)}</span> {jurisdictionName(part)}
                  <CommandShortcut>{part}</CommandShortcut>
                </CommandItem>
              )}
              {named.map(({ code, name }) => (
                <CommandItem key={code} value={`${name} ${code}`} onSelect={() => onChange(code)}>
                  <span aria-hidden>{flag(code)}</span> {name}
                  {value === code && <CheckIcon />}
                  <CommandShortcut>{covered.includes(code) ? `${code} · has a source` : code}</CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </Command>
  )
}

// The inputs the Settings page edits casebench.yaml with: text, numbers, choices, lists, named
// options and JSON, each with a label a person can read (decision 0063).

import { useId, useState } from "react"
import { PlusIcon, XIcon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type Help = { label: string; description?: React.ReactNode; className?: string }

export function TextField({
  label,
  description,
  value,
  onChange,
  placeholder,
  className,
  type = "text",
}: Help & {
  value: string | null | undefined
  onChange: (value: string | null) => void
  placeholder?: string
  type?: "text" | "url"
}) {
  const id = useId()
  return (
    <Field className={className}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        type={type}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
    </Field>
  )
}

export function NumberField({
  label,
  description,
  value,
  onChange,
  placeholder,
  className,
  step = "any",
  min,
}: Help & {
  value: number | null | undefined
  onChange: (value: number | null) => void
  placeholder?: string
  step?: string
  min?: number
}) {
  const id = useId()
  return (
    <Field className={className}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        type="number"
        inputMode="decimal"
        step={step}
        min={min}
        value={value ?? ""}
        placeholder={placeholder}
        onChange={(event) => {
          const text = event.target.value
          onChange(text === "" || Number.isNaN(Number(text)) ? null : Number(text))
        }}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
    </Field>
  )
}

export function ChoiceField({
  label,
  description,
  value,
  choices,
  onChange,
  className,
  placeholder = "Choose",
}: Help & {
  value: string | null | undefined
  choices: { value: string; label: string }[]
  onChange: (value: string) => void
  placeholder?: string
}) {
  const id = useId()
  // A value the file holds stays a choice even when nothing installed offers it.
  const listed =
    value && !choices.some((c) => c.value === value) ? [...choices, { value, label: value }] : choices
  return (
    <Field className={className}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Select value={value ?? undefined} onValueChange={onChange}>
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {listed.map((choice) => (
            <SelectItem key={choice.value} value={choice.value}>
              {choice.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {description && <FieldDescription>{description}</FieldDescription>}
    </Field>
  )
}

export function CheckField({
  label,
  description,
  checked,
  onChange,
  className,
}: Help & { checked: boolean; onChange: (checked: boolean) => void }) {
  const id = useId()
  return (
    <Field orientation="horizontal" className={cn("items-start", className)}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 size-4 shrink-0 accent-primary"
      />
      <div className="flex flex-col gap-1">
        <FieldLabel htmlFor={id} className="font-normal">
          {label}
        </FieldLabel>
        {description && <FieldDescription>{description}</FieldDescription>}
      </div>
    </Field>
  )
}

/** Several boxes for a list that holds some of a few known words. */
export function PickField({
  label,
  description,
  options,
  values,
  onChange,
  className,
}: Help & {
  options: { value: string; label: string }[]
  values: string[]
  onChange: (values: string[]) => void
}) {
  return (
    <fieldset className={cn("flex flex-col gap-2", className)}>
      <legend className="mb-2 text-sm font-medium">{label}</legend>
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {options.map((option) => (
          <label key={option.value} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="size-4 accent-primary"
              checked={values.includes(option.value)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? [...values, option.value]
                    : values.filter((v) => v !== option.value),
                )
              }
            />
            {option.label}
          </label>
        ))}
      </div>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
    </fieldset>
  )
}

/** A list of short words, such as hosts or jurisdiction codes: type one and press Enter. */
export function TagsField({
  label,
  description,
  values,
  onChange,
  placeholder,
  className,
}: Help & { values: string[]; onChange: (values: string[]) => void; placeholder?: string }) {
  const id = useId()
  const [typed, setTyped] = useState("")
  function add() {
    const word = typed.trim()
    if (word && !values.includes(word)) onChange([...values, word])
    setTyped("")
  }
  return (
    <Field className={className}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      {values.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label={label}>
          {values.map((value) => (
            <li key={value}>
              <Badge variant="secondary" className="gap-1 pr-1 font-mono">
                {value}
                <button
                  type="button"
                  aria-label={`Remove ${value}`}
                  onClick={() => onChange(values.filter((v) => v !== value))}
                  className="rounded-sm p-0.5 hover:bg-foreground/10"
                >
                  <XIcon className="size-3" />
                </button>
              </Badge>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Input
          id={id}
          value={typed}
          placeholder={placeholder}
          onChange={(event) => setTyped(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault()
              add()
            }
          }}
        />
        <Button type="button" variant="outline" onClick={add} disabled={!typed.trim()}>
          Add
        </Button>
      </div>
      {description && <FieldDescription>{description}</FieldDescription>}
    </Field>
  )
}

/** A value as the page shows it: text as it is, anything else as JSON. */
export function shown(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value)
}

/** What a typed value means: a number, true, false, null, a list or a map when it reads as
 * JSON, and text otherwise. */
export function parsed(text: string): unknown {
  const trimmed = text.trim()
  if (trimmed === "") return ""
  if (/^(-?\d|true$|false$|null$|\[|\{)/.test(trimmed)) {
    try {
      return JSON.parse(trimmed)
    } catch {
      return text
    }
  }
  return text
}

/** Named options, such as a provider's `base_url` and `max_tokens`. */
export function OptionsField({
  label,
  description,
  value,
  onChange,
  suggestions = [],
  className,
  noun = "option",
}: Help & {
  value: Record<string, unknown>
  onChange: (value: Record<string, unknown>) => void
  suggestions?: string[]
  /** What one entry is called, such as option, header or variable. */
  noun?: string
}) {
  const rows = Object.entries(value)
  const [name, setName] = useState("")
  const unused = suggestions.filter((s) => !(s in value))
  function add(named: string) {
    const key = named.trim()
    if (key && !(key in value)) onChange({ ...value, [key]: "" })
    setName("")
  }
  return (
    <fieldset className={cn("flex flex-col gap-2", className)}>
      <legend className="mb-2 text-sm font-medium">{label}</legend>
      {rows.length > 0 && (
        <div className="flex flex-col gap-2">
          {rows.map(([key, item]) => (
            <div key={key} className="grid grid-cols-[minmax(7rem,12rem)_1fr_auto] items-center gap-2">
              <code className="truncate rounded bg-muted px-2 py-1.5 text-xs" title={key}>
                {key}
              </code>
              <Input
                aria-label={key}
                value={shown(item)}
                onChange={(event) => onChange({ ...value, [key]: parsed(event.target.value) })}
                className="font-mono text-xs"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove ${key}`}
                onClick={() => {
                  const next = { ...value }
                  delete next[key]
                  onChange(next)
                }}
              >
                <XIcon />
              </Button>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Input
          aria-label={`New ${noun} for ${label}`}
          value={name}
          placeholder={`${noun} name`}
          className="max-w-56 font-mono text-xs"
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault()
              add(name)
            }
          }}
        />
        <Button type="button" variant="outline" size="sm" onClick={() => add(name)} disabled={!name.trim()}>
          <PlusIcon /> Add {noun}
        </Button>
        {unused.map((suggested) => (
          <Button key={suggested} type="button" variant="ghost" size="sm" onClick={() => add(suggested)}>
            <PlusIcon /> {suggested}
          </Button>
        ))}
      </div>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
    </fieldset>
  )
}

/** Anything casebench.yaml holds, as JSON, for settings with no form of their own. */
export function JsonField({
  label,
  description,
  value,
  onChange,
  className,
  rows = 6,
}: Help & { value: unknown; onChange: (value: unknown) => void; rows?: number }) {
  const id = useId()
  const [text, setText] = useState(() => JSON.stringify(value ?? null, null, 2))
  const [error, setError] = useState<string | null>(null)
  return (
    <Field className={className} data-invalid={error ? true : undefined}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Textarea
        id={id}
        rows={rows}
        value={text}
        spellCheck={false}
        className="font-mono text-xs"
        aria-invalid={error ? true : undefined}
        onChange={(event) => {
          setText(event.target.value)
          try {
            onChange(event.target.value.trim() ? JSON.parse(event.target.value) : null)
            setError(null)
          } catch {
            setError("This is not JSON yet; it is saved once it is.")
          }
        }}
      />
      {error ? <FieldError>{error}</FieldError> : description && <FieldDescription>{description}</FieldDescription>}
    </Field>
  )
}

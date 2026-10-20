// What is set up and what is missing, read from casebench.yaml as the Settings page shows it
// (decision 0065). Home, the guide and the sidebar all read it from here.

import type { KeyView, ModelView, SettingsView } from "@/lib/api"

export type Corpus = {
  connector?: string
  jurisdictions?: string[]
  holds?: string[]
  options?: Record<string, unknown>
  probe?: string
  [field: string]: unknown
}

export type Target = { type?: string; entry?: string; url?: string; run?: string; [field: string]: unknown }

export interface SetupProgress {
  agent: string | null
  corpora: Record<string, Corpus>
  /** Every code a source names; a source that names none covers every jurisdiction. */
  jurisdictions: string[]
  everywhere: string[]
  judge: ModelView | null
  secondJudge: ModelView | null
  extraction: ModelView[]
  missingKeys: KeyView[]
  done: number
  total: number
  complete: boolean
}

/** How the agent is reached, in a few words. */
export function describeTarget(target: Target | undefined | null): string | null {
  if (!target || !target.type) return null
  if (target.type === "python") return `Python function ${target.entry ?? ""}`.trim()
  if (target.type === "http") return `HTTP endpoint ${target.url ?? ""}`.trim()
  if (target.type === "command") return `Command ${target.run ?? ""}`.trim()
  return `${target.type} plugin`
}

/** What kind of source a corpus reads, in a person's words. */
export function sourceKind(corpus: Corpus): string {
  switch (corpus.connector) {
    case "folder":
      return "Folder on this machine"
    case "http":
      return "Document API"
    case "mcp":
      return "MCP server"
    default:
      return corpus.connector ? `${corpus.connector} plugin` : "Source"
  }
}

/** Where the source is: a folder's path, an API's address or a server's command. */
export function sourcePlace(corpus: Corpus): string | null {
  const options = corpus.options ?? {}
  const place = options.path ?? options.base_url ?? options.url ?? options.command
  if (Array.isArray(place)) return place.join(" ")
  return typeof place === "string" ? place : null
}

export function progress(view: SettingsView): SetupProgress {
  const sections = view.sections
  const corpora = (sections.corpora as Record<string, Corpus> | undefined) ?? {}
  const codes = new Set<string>()
  const everywhere: string[] = []
  for (const [name, corpus] of Object.entries(corpora)) {
    const named = corpus.jurisdictions ?? []
    if (!named.length) everywhere.push(name)
    named.forEach((code) => codes.add(code))
  }
  const judge = view.models.find((m) => m.role === "judge") ?? null
  const secondJudge = view.models.find((m) => m.role === "second judge") ?? null
  const extraction = view.models.filter((m) => m.role.startsWith("extraction"))
  const missingKeys = view.keys.filter((k) => k.where === "missing")
  const agent = describeTarget(sections.target as Target | undefined)
  const steps = [agent !== null, Object.keys(corpora).length > 0, judge !== null, missingKeys.length === 0]
  const done = steps.filter(Boolean).length
  return {
    agent,
    corpora,
    jurisdictions: [...codes].sort(),
    everywhere,
    judge,
    secondJudge,
    extraction,
    missingKeys,
    done,
    total: steps.length,
    complete: done === steps.length && !view.problem,
  }
}

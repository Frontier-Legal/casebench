// What the screen calls things, in a lawyer's words.

import type { CitationView } from "@/lib/api"

const FACT_KINDS: Record<string, string> = {
  outcome: "Ruling",
  statute: "Statute",
  precedent: "Precedent",
  answer: "Expected answer",
  "key point": "Key point",
  issue: "Issue",
  expected: "Expected value",
}

export function factKind(kind: string | null | undefined): string {
  if (!kind) return "Point"
  return FACT_KINDS[kind] ?? kind.charAt(0).toUpperCase() + kind.slice(1)
}

const INPUTS: Record<string, string> = {
  question: "Question",
  instruction: "Instruction",
  facts: "Facts",
  constraints: "Limits",
  document: "Document",
  fields: "Fields to take",
}

export function inputName(name: string): string {
  return INPUTS[name] ?? name
}

export const CITATION_LABELS: Record<CitationView["label"], { short: string; long: string }> = {
  verified: { short: "Supported", long: "The source says what the answer claims." },
  misgrounded: { short: "Misused", long: "The source exists but says something else." },
  fabricated: { short: "Not found", long: "No source in the corpus matches this citation." },
  unchecked: { short: "Not checked", long: "No connected corpus covers this kind of source." },
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`
}

const TASKS: Record<string, string> = {
  qa: "Legal question",
  outcome: "Ruling",
  statute: "Statutes",
  precedent: "Precedents",
  research: "Research",
  drafting: "Drafting",
  editing: "Editing",
  extraction: "Extraction",
}

export function taskName(task: string): string {
  return TASKS[task] ?? task
}

// SPDX-License-Identifier: Elastic-2.0
// The audit log: every decision and team event, who, when, before, after and why; it is only ever
// read (decision 0058).

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { SearchIcon } from "lucide-react"

import { Section } from "@/components/section"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { team, type AuditEntry } from "./api"

const ACTIONS: Record<string, string> = {
  verdict: "Gave a verdict",
  finished: "Finished an item",
  changed: "Changed a case",
  created: "Wrote a case",
  proposed: "Proposed a change",
  approved: "Approved",
  rejected: "Rejected",
  preferred: "Compared two answers",
  tried: "Tried a question",
  invited: "Invited",
  "changed person": "Changed a person",
  "signed in": "Signed in",
  "created key": "Created an API key",
  "revoked key": "Revoked an API key",
  "changed limits": "Changed spend limits",
}

function shown(value: unknown): string {
  if (value === null || value === undefined) return ""
  if (typeof value === "string") return value
  const text = JSON.stringify(value)
  return text.length > 160 ? `${text.slice(0, 160)}…` : text
}

/** Newest first, a page at a time. */
export function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [query, setQuery] = useState("")
  const [more, setMore] = useState(false)

  const load = useCallback(async (search: string, before?: number) => {
    try {
      const page = await team.audit(search, before)
      setEntries((now) => (before ? [...now, ...page] : page))
      setMore(page.length >= 200)
    } catch (failure) {
      toast.error(failure instanceof Error ? failure.message : String(failure))
    }
  }, [])

  useEffect(() => {
    load("")
  }, [load])

  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Audit log</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Every verdict, change to golden data and team event, with who, when, what it was before and after,
          and why. Nothing in it can be changed or removed.
        </p>
      </div>
      <Section
        title="Events"
        action={
          <form
            onSubmit={(event) => {
              event.preventDefault()
              load(query)
            }}
            className="flex items-center gap-2"
          >
            <Input
              aria-label="Search the log"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="A name, a case, a reason"
              className="h-8 w-56"
            />
            <Button type="submit" size="icon" variant="outline" aria-label="Search">
              <SearchIcon />
            </Button>
          </form>
        }
      >
        <Table aria-label="Audit log">
          <TableHeader>
            <TableRow>
              <TableHead>When</TableHead>
              <TableHead>Who</TableHead>
              <TableHead>What</TableHead>
              <TableHead>Change</TableHead>
              <TableHead>Why</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((entry) => (
              <TableRow key={entry.id} className="align-top">
                <TableCell className="text-xs whitespace-nowrap text-muted-foreground tabular-nums">
                  {new Date(entry.at).toLocaleString()}
                </TableCell>
                <TableCell className="font-medium">{entry.by}</TableCell>
                <TableCell>
                  <div>{ACTIONS[entry.action] ?? entry.action}</div>
                  <div className="max-w-xs truncate text-xs text-muted-foreground">{entry.subject}</div>
                </TableCell>
                <TableCell className="max-w-md text-xs">
                  {entry.before !== null && entry.before !== undefined && (
                    <div className="truncate text-muted-foreground line-through">{shown(entry.before)}</div>
                  )}
                  <div className="truncate">{shown(entry.after)}</div>
                </TableCell>
                <TableCell className="max-w-xs text-sm">{entry.reason}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {more && (
          <div className="mt-4 flex justify-center">
            <Button variant="outline" onClick={() => load(query, entries[entries.length - 1]?.id)}>
              Older events
            </Button>
          </div>
        )}
      </Section>
    </div>
  )
}

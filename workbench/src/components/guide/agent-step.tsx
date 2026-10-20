// The guide's first step: how Casebench reaches the agent, picked from the functions the code
// scan found, or an HTTP endpoint, or a command (decisions 0043, 0065).

import { useEffect, useState } from "react"
import { CodeIcon, GlobeIcon, SquareTerminalIcon } from "lucide-react"

import { JsonField, TextField } from "@/components/settings/fields"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { api, type ScanView } from "@/lib/api"
import type { Target } from "@/lib/setup-progress"
import { cn } from "@/lib/utils"

function Choice({
  checked,
  onClick,
  icon: Icon,
  title,
  text,
}: {
  checked: boolean
  onClick: () => void
  icon: React.ElementType
  title: React.ReactNode
  text: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={checked}
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 rounded-xl border p-4 text-left transition hover:border-primary/50 hover:bg-accent/40",
        checked && "border-primary bg-accent/60 ring-1 ring-primary/30",
      )}
    >
      <Icon className="mt-0.5 size-5 shrink-0 text-primary" />
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="font-medium break-all">{title}</span>
        <span className="text-sm text-muted-foreground">{text}</span>
      </span>
    </button>
  )
}

export function AgentStep({ target, onChange }: { target: Target | null; onChange: (target: Target) => void }) {
  const [found, setFound] = useState<ScanView | null>(null)
  const [entry, setEntry] = useState("")

  useEffect(() => {
    api
      .scan()
      .then((scan) => {
        setFound(scan)
        // Suggested, not chosen: the only function there is, as Quick start takes it (0043).
        if (!target && scan.entries.length === 1) onChange({ type: "python", entry: scan.entries[0] })
      })
      .catch(() => setFound({ said: "", entries: [], clients: [], models: [] }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!found) return <Skeleton className="h-48" />
  const kind = target?.type ?? null
  const listed = kind === "python" && target?.entry && found.entries.includes(target.entry)

  return (
    <div className="flex flex-col gap-6">
      {(found.clients.length > 0 || found.models.length > 0) && (
        <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-3 text-sm">
          <span className="font-medium">Found in your code</span>
          <div className="flex flex-wrap gap-1.5">
            {found.models.map((model) => (
              <Badge key={model} variant="secondary" className="font-mono">
                {model}
              </Badge>
            ))}
            {found.clients.map((client) => (
              <Badge key={client} variant="outline" className="font-mono">
                {client}
              </Badge>
            ))}
          </div>
          <span className="text-xs text-muted-foreground">{found.said}</span>
        </div>
      )}
      <div role="radiogroup" aria-label="How Casebench reaches your agent" className="grid gap-3">
        {found.entries.map((name) => (
          <Choice
            key={name}
            checked={kind === "python" && target?.entry === name}
            onClick={() => onChange({ type: "python", entry: name })}
            icon={CodeIcon}
            title={<code>{name}</code>}
            text="A function in your project that answers a question. Casebench calls it as your app does."
          />
        ))}
        <Choice
          checked={kind === "python" && !listed}
          onClick={() => onChange({ type: "python", entry: entry || "" })}
          icon={CodeIcon}
          title={found.entries.length ? "Another Python function" : "A Python function"}
          text="Written as path.py:function, taking the question and returning the answer."
        />
        <Choice
          checked={kind === "http"}
          onClick={() => onChange({ type: "http", url: "", body: { question: "{question}" }, answer: "$.answer" })}
          icon={GlobeIcon}
          title="An HTTP endpoint"
          text="A deployed service in any language: Casebench posts each question and reads the answer."
        />
        <Choice
          checked={kind === "command"}
          onClick={() => onChange({ type: "command", run: "" })}
          icon={SquareTerminalIcon}
          title="A command"
          text="A program Casebench starts with the question, reading the answer it prints."
        />
      </div>
      {kind === "python" && !listed && (
        <TextField
          label="The function"
          placeholder="agent.py:answer"
          value={target?.entry ?? entry}
          onChange={(value) => {
            setEntry(value ?? "")
            onChange({ type: "python", entry: value ?? "" })
          }}
        />
      )}
      {kind === "http" && (
        <div className="grid gap-4">
          <TextField
            label="Endpoint"
            type="url"
            placeholder="https://agent.firm.internal/ask"
            value={target?.url}
            onChange={(url) => onChange({ ...target, type: "http", url: url ?? "" })}
          />
          <JsonField
            label="Request body"
            description="JSON, with {question} where the question goes."
            rows={3}
            value={target?.body ?? {}}
            onChange={(body) => onChange({ ...target, type: "http", body })}
          />
          <TextField
            label="Where the answer is in the response"
            description="A JSONPath, such as $.answer."
            value={target?.answer as string | undefined}
            onChange={(answer) => onChange({ ...target, type: "http", answer: answer ?? "" })}
          />
        </div>
      )}
      {kind === "command" && (
        <TextField
          label="The command"
          description="With {question} where the question goes."
          placeholder="python ask.py {question}"
          value={target?.run}
          onChange={(run) => onChange({ type: "command", run: run ?? "" })}
        />
      )}
    </div>
  )
}

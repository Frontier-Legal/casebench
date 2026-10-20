// Connect an MCP server: how it is reached, the tool that searches and the one that fetches,
// picked from the tools it lists, then the fields picked from what it returned (0065).

import { useId, useState } from "react"
import { ListIcon } from "lucide-react"

import { FieldPicker, type Found } from "@/components/jurisdictions/field-picker"
import { TextField } from "@/components/settings/fields"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { api, type McpAsked, type Tool } from "@/lib/api"
import { message } from "@/lib/use-settings"

function ToolPick({
  label,
  tools,
  value,
  onChange,
}: {
  label: string
  tools: Tool[]
  value: string
  onChange: (tool: string) => void
}) {
  const id = useId()
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm shadow-xs focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        <option value="">Choose a tool</option>
        {tools.map((tool) => (
          <option key={tool.name} value={tool.name}>
            {tool.name}
            {tool.description ? ` — ${tool.description}` : ""}
          </option>
        ))}
      </select>
    </Field>
  )
}

export function McpSource({ jurisdiction, onReady }: { jurisdiction: string; onReady: (found: Found) => void }) {
  const [where, setWhere] = useState("")
  const [tools, setTools] = useState<Tool[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [asked, setAsked] = useState<Omit<McpAsked, "command" | "url">>({
    search_tool: "",
    search_arg: "query",
    fetch_tool: "",
    fetch_arg: "id",
    probe: "",
    jurisdictions: [jurisdiction],
  })
  const reach = where.trim().startsWith("http") ? { url: where.trim() } : { command: where.trim() }
  const put = (patch: Partial<McpAsked>) => {
    setAsked({ ...asked, ...patch })
    onReady(null)
  }

  async function list() {
    setBusy(true)
    setError(null)
    try {
      setTools(await api.mcpTools(reach))
    } catch (caught) {
      setTools(null)
      setError(message(caught))
    } finally {
      setBusy(false)
    }
  }

  const ready = Boolean(asked.search_tool && asked.fetch_tool && asked.probe)
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <TextField
          label="How to reach the server"
          description="Its URL, or the command that starts it on this machine."
          placeholder="https://mcp.provider.example/mcp  or  npx legal-docs-mcp"
          value={where}
          onChange={(value) => {
            setWhere(value ?? "")
            setTools(null)
            onReady(null)
          }}
        />
        <div>
          <Button type="button" variant="outline" onClick={list} disabled={!where.trim() || busy}>
            {busy ? <Spinner /> : <ListIcon />} List its tools
          </Button>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      {tools && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <ToolPick label="The tool that searches" tools={tools} value={asked.search_tool} onChange={(search_tool) => put({ search_tool })} />
            <TextField
              label="Its argument for the search words"
              value={asked.search_arg}
              onChange={(search_arg) => put({ search_arg: search_arg ?? "" })}
            />
            <ToolPick label="The tool that returns a document" tools={tools} value={asked.fetch_tool} onChange={(fetch_tool) => put({ fetch_tool })} />
            <TextField
              label="Its argument for the document's id"
              value={asked.fetch_arg}
              onChange={(fetch_arg) => put({ fetch_arg: fetch_arg ?? "" })}
            />
            <TextField
              label="A search that finds a document"
              className="sm:col-span-2"
              value={asked.probe}
              onChange={(probe) => put({ probe: probe ?? "" })}
            />
          </div>
          <FieldPicker
            key={JSON.stringify([where, asked])}
            ready={ready}
            onReady={onReady}
            connect={(picks) => api.connectMcp({ ...reach, ...asked, ...picks })}
          />
        </>
      )}
    </div>
  )
}

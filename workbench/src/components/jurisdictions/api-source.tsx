// Connect a document API: its address, its key and a search, then the fields picked from what
// the API returned (decision 0065).

import { useState } from "react"

import { FieldPicker, type Found } from "@/components/jurisdictions/field-picker"
import { TextField } from "@/components/settings/fields"
import { KeyLine } from "@/components/setup/model-card"
import { api, type ApiAsked, type SettingsView } from "@/lib/api"

export function ApiSource({
  view,
  onView,
  jurisdiction,
  onReady,
}: {
  view: SettingsView
  onView: (view: SettingsView) => void
  jurisdiction: string
  onReady: (found: Found) => void
}) {
  const [asked, setAsked] = useState<ApiAsked>({
    base_url: "",
    search_path: "/search",
    fetch_path: "/documents/{id}",
    key_env: "",
    probe: "",
    jurisdictions: [jurisdiction],
  })
  const put = (patch: Partial<ApiAsked>) => {
    setAsked({ ...asked, ...patch })
    onReady(null)
  }
  const ready = Boolean(asked.base_url && asked.search_path && asked.fetch_path.includes("{id}") && asked.probe)
  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="The API's address"
          type="url"
          placeholder="https://api.provider.example/v1"
          description="A provider's data API or your firm's own; a variable such as ${DOCS_URL} works too."
          className="sm:col-span-2"
          value={asked.base_url}
          onChange={(base_url) => put({ base_url: base_url ?? "" })}
        />
        <TextField
          label="Search path"
          description="Under that address; the search words go in its q parameter."
          value={asked.search_path}
          onChange={(search_path) => put({ search_path: search_path ?? "" })}
        />
        <TextField
          label="Document path"
          description="With {id} where a document's id goes."
          value={asked.fetch_path}
          onChange={(fetch_path) => put({ fetch_path: fetch_path ?? "" })}
        />
        <TextField
          label="Key variable"
          description="The environment variable that holds the API key; empty when it needs none."
          placeholder="DOCS_API_KEY"
          value={asked.key_env}
          onChange={(key_env) => put({ key_env: key_env?.toUpperCase() ?? "" })}
        />
        <TextField
          label="A search that finds a document"
          description="Words a decision in this source contains; checks run it too."
          value={asked.probe}
          onChange={(probe) => put({ probe: probe ?? "" })}
        />
      </div>
      {asked.key_env && <KeyLine name={asked.key_env} keys={view.keys} onView={onView} />}
      <FieldPicker
        key={JSON.stringify(asked)}
        ready={ready}
        onReady={onReady}
        connect={(picks) => api.connectApi({ ...asked, key_env: asked.key_env || null, ...picks })}
      />
    </div>
  )
}

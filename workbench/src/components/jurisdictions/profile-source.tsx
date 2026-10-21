// Connect a source from a provider's profile: one bundled with Casebench or a file the
// provider gave, checked with one live search and fetch using the key here (0033, 0065).

import { useEffect, useState } from "react"
import { BadgeCheckIcon } from "lucide-react"

import type { Found } from "@/components/jurisdictions/field-picker"
import { TextField } from "@/components/settings/fields"
import { ChoiceCards } from "@/components/setup/choice-cards"
import { KeyLine } from "@/components/setup/model-card"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { api, type FromProfile, type ProfileView, type SettingsView } from "@/lib/api"
import { message } from "@/lib/use-settings"

export function ProfileSource({
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
  const [bundled, setBundled] = useState<ProfileView[]>([])
  const [given, setGiven] = useState("")
  const [found, setFound] = useState<FromProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.profiles().then(setBundled).catch(() => setBundled([]))
  }, [])

  const chosen = bundled.find((p) => p.id === given)
  async function connect() {
    setBusy(true)
    setError(null)
    try {
      const shown = await api.connectProfile(given.trim(), [jurisdiction])
      setFound(shown)
      onReady({ name: shown.name, block: shown.block })
    } catch (caught) {
      setFound(null)
      setError(message(caught))
      onReady(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {bundled.length > 0 && (
        <ChoiceCards
          label="Profiles bundled with Casebench"
          className="sm:grid-cols-2"
          value={chosen ? given : null}
          onChange={(id) => {
            setGiven(id)
            onReady(null)
          }}
          choices={bundled.map((item) => ({ value: item.id, title: item.name, text: item.jurisdictions.join(", ") }))}
        />
      )}
      <TextField
        label={bundled.length ? "Or a profile file" : "Profile file"}
        description="The .yaml profile your data provider gives you, relative to this project. It holds no key, only the variable it is read from."
        placeholder="provider-profile.yaml"
        value={chosen ? "" : given}
        onChange={(value) => {
          setGiven(value ?? "")
          onReady(null)
        }}
      />
      {chosen?.key_env && <KeyLine name={chosen.key_env} keys={view.keys} onView={onView} />}
      <div>
        <Button type="button" onClick={connect} disabled={!given.trim() || busy}>
          {busy ? <Spinner /> : <BadgeCheckIcon />} Connect with this profile
        </Button>
      </div>
      {error && <p className="text-sm break-words text-destructive">{error}</p>}
      {found && (
        <ul className="flex flex-col gap-1 rounded-lg border border-success/30 bg-success/8 p-3 text-sm">
          {found.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

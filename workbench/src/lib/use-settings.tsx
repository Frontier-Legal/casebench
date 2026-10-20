// The setup as the Settings page reads it, loaded once per page, and saved one section at a time
// after asking before comments in casebench.yaml are dropped (decisions 0042, 0063, 0065).

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api, type SettingsView } from "@/lib/api"

export function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export interface Settings {
  view: SettingsView | null
  setView: (view: SettingsView) => void
  /** True when the section was saved; a refusal is shown as a toast and returns false. */
  save: (section: string, value: unknown) => Promise<boolean>
  reload: () => Promise<void>
  /** The question asked before a save drops comments; render it once on the page. */
  asking: React.ReactNode
}

export function useSettings(): Settings {
  const [view, setView] = useState<SettingsView | null>(null)
  const [asking, setAsking] = useState(false)
  const answer = useRef<((go: boolean) => void) | null>(null)
  const accepted = useRef(false)
  const comments = useRef(false)
  comments.current = view?.has_comments ?? false

  const reload = useCallback(async () => setView(await api.settings()), [])
  useEffect(() => {
    reload().catch((error) => toast.error(message(error)))
  }, [reload])

  const save = useCallback(async (section: string, value: unknown) => {
    if (comments.current && !accepted.current) {
      setAsking(true)
      const go = await new Promise<boolean>((resolve) => {
        answer.current = resolve
      })
      setAsking(false)
      accepted.current = go
      if (!go) return false
    }
    try {
      setView(await api.saveSection(section, value))
      return true
    } catch (error) {
      toast.error(message(error))
      return false
    }
  }, [])

  const question = (
    <Dialog open={asking} onOpenChange={(open) => !open && answer.current?.(false)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Comments in casebench.yaml will be dropped</DialogTitle>
          <DialogDescription>
            Saving rewrites the file with its header, as casebench init does, so other comments go. To keep them,
            change the file in Settings, under File.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => answer.current?.(false)}>
            Cancel
          </Button>
          <Button onClick={() => answer.current?.(true)}>Save anyway</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )

  return { view, setView, save, reload, asking: question }
}

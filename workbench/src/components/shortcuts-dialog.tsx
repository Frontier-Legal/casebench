import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import { SHORTCUTS } from "@/lib/keys"

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
          <DialogDescription>
            Work through the queue without the mouse. On a phone or tablet, tap the buttons instead.
          </DialogDescription>
        </DialogHeader>
        <ul className="flex flex-col gap-3" aria-label="Shortcuts">
          {SHORTCUTS.map((shortcut) => (
            <li key={shortcut.what} className="flex items-center justify-between gap-4 text-sm">
              <span>{shortcut.what}</span>
              <KbdGroup>
                {shortcut.keys.map((key) =>
                  key === "–" ? (
                    <span key={key}>–</span>
                  ) : (
                    <Kbd key={key}>{key}</Kbd>
                  ),
                )}
              </KbdGroup>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  )
}

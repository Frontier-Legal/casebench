// Keyboard first (decision 0050): 1 to 9 pick a choice on the focused row, arrows or J and K
// move between rows, Cmd+Enter or Ctrl+Enter finishes the item, ? lists the shortcuts.

import { useEffect, useRef } from "react"

export interface Shortcuts {
  choose?: (n: number) => void
  move?: (by: number) => void
  finish?: () => void
  help?: () => void
}

export const SHORTCUTS: { keys: string[]; what: string }[] = [
  { keys: ["1", "–", "9"], what: "Pick the numbered choice on the highlighted row" },
  { keys: ["↓", "J"], what: "Next row" },
  { keys: ["↑", "K"], what: "Previous row" },
  { keys: ["⌘", "Enter"], what: "Finish and open the next item (Ctrl+Enter on Windows and Linux)" },
  { keys: ["Esc"], what: "Leave a text box" },
  { keys: ["?"], what: "Show these shortcuts" },
]

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

export function useShortcuts(handlers: Shortcuts, enabled = true): void {
  const latest = useRef(handlers)
  latest.current = handlers

  useEffect(() => {
    if (!enabled) return
    function onKey(event: KeyboardEvent) {
      const now = latest.current
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        now.finish?.()
        return
      }
      if (typing(event.target)) {
        if (event.key === "Escape") (event.target as HTMLElement).blur()
        return
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (event.key === "?") {
        event.preventDefault()
        now.help?.()
      } else if (/^[1-9]$/.test(event.key)) {
        event.preventDefault()
        now.choose?.(Number(event.key))
      } else if (event.key === "ArrowDown" || event.key === "j") {
        event.preventDefault()
        now.move?.(1)
      } else if (event.key === "ArrowUp" || event.key === "k") {
        event.preventDefault()
        now.move?.(-1)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled])
}

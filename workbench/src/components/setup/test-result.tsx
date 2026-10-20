// A live test of one part, a source or a model, and what to do when it did not pass (0065).

import { useState } from "react"
import { CircleCheckIcon, CircleXIcon, PlugZapIcon, WifiOffIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Tested } from "@/lib/api"
import { message } from "@/lib/use-settings"
import { cn } from "@/lib/utils"

export function TestResult({ tested, className }: { tested: Tested; className?: string }) {
  const unreachable = tested.status === "not reachable from here"
  const Icon = tested.passed ? CircleCheckIcon : unreachable ? WifiOffIcon : CircleXIcon
  return (
    <div
      role="status"
      className={cn(
        "flex gap-2.5 rounded-lg border p-3 text-sm",
        tested.passed
          ? "border-success/30 bg-success/8"
          : unreachable
            ? "border-warning/40 bg-warning/10"
            : "border-destructive/30 bg-destructive/8",
        className,
      )}
    >
      <Icon
        className={cn(
          "mt-0.5 size-4 shrink-0",
          tested.passed ? "text-success" : unreachable ? "text-warning" : "text-destructive",
        )}
      />
      <div className="flex min-w-0 flex-col gap-1">
        <span className="font-medium">
          {tested.passed ? "It works" : unreachable ? "Not reachable from this machine" : "It did not work"}
        </span>
        {tested.reason && <span className="break-words text-muted-foreground">{tested.reason}</span>}
        {tested.next && <span className="break-words">Next: {tested.next}</span>}
      </div>
    </div>
  )
}

/** A button that runs one live test and shows its result under it. */
export function TestButton({
  label,
  test,
  disabled,
  onTested,
}: {
  label: string
  test: () => Promise<Tested>
  disabled?: boolean
  onTested?: (tested: Tested) => void
}) {
  const [busy, setBusy] = useState(false)
  const [tested, setTested] = useState<Tested | null>(null)
  async function run() {
    setBusy(true)
    try {
      const found = await test()
      setTested(found)
      onTested?.(found)
    } catch (error) {
      setTested({ part: label, status: "failed", passed: false, reason: message(error), next: "" })
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="flex flex-col gap-2">
      <div>
        <Button type="button" variant="outline" size="sm" onClick={run} disabled={busy || disabled}>
          {busy ? <Spinner /> : <PlugZapIcon />} {label}
        </Button>
      </div>
      {tested && <TestResult tested={tested} />}
    </div>
  )
}

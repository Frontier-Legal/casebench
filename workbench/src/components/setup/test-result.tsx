// A live test of one part, a source or a model, and what to do when it did not pass (0065).

import { useState } from "react"
import { CircleCheckIcon, CircleXIcon, PlugZapIcon, WifiOffIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Tested } from "@/lib/api"
import { message } from "@/lib/use-settings"

export function TestResult({ tested }: { tested: Tested }) {
  const unreachable = tested.status === "not reachable from here"
  const Icon = tested.passed ? CircleCheckIcon : unreachable ? WifiOffIcon : CircleXIcon
  return (
    <Alert variant={tested.passed || unreachable ? "default" : "destructive"}>
      <Icon />
      <AlertTitle>
        {tested.passed ? "It works" : unreachable ? "Not reachable from this machine" : "It did not work"}
      </AlertTitle>
      <AlertDescription>
        {tested.reason && <p className="break-words">{tested.reason}</p>}
        {tested.next && <p className="break-words">Next: {tested.next}</p>}
      </AlertDescription>
    </Alert>
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

// SPDX-License-Identifier: Elastic-2.0
// In front of the workbench until someone is signed in: the first admin's setup, then sign-in by
// emailed link, by Google or Microsoft, or by password (decision 0058).

import { useEffect, useState } from "react"
import { KeyRoundIcon, MailIcon, ScaleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldSeparator } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"

import { team, type TeamStatus } from "./api"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function Frame({ title, lead, children }: { title: string; lead: string; children: React.ReactNode }) {
  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 p-6">
      <div className="flex w-full max-w-sm flex-col gap-6 rounded-xl border bg-card p-6 shadow-xs sm:p-8">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ScaleIcon className="size-5" />
          </div>
          <span className="text-lg font-semibold tracking-tight">Casebench</span>
        </div>
        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{lead}</p>
        </div>
        {children}
      </div>
    </main>
  )
}

function Setup({ onDone }: { onDone: () => void }) {
  const [code, setCode] = useState("")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await team.setup(code, name, email, password)
      onDone()
    } catch (failure) {
      setError(message(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Frame
      title="Set up your team"
      lead="No one is in this team yet. Create the first admin, who invites everyone else."
    >
      <form onSubmit={submit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="setup-code">Setup code</FieldLabel>
            <Input id="setup-code" value={code} onChange={(e) => setCode(e.target.value)} autoFocus placeholder="ABCD-EFGH-JKLM" className="font-mono uppercase" />
            <FieldDescription>Printed in the server's log when it started.</FieldDescription>
          </Field>
          <Field>
            <FieldLabel htmlFor="setup-name">Your name</FieldLabel>
            <Input id="setup-name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          </Field>
          <Field>
            <FieldLabel htmlFor="setup-email">Email</FieldLabel>
            <Input id="setup-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </Field>
          <Field data-invalid={Boolean(error)}>
            <FieldLabel htmlFor="setup-password">Password</FieldLabel>
            <Input
              id="setup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            <FieldDescription className={error ? "text-destructive" : undefined}>
              {error ?? "12 characters at least, and no default or common password."}
            </FieldDescription>
          </Field>
          <Button type="submit" className="h-10" disabled={busy || !code || !name || !email || !password}>
            {busy && <Spinner />} Create the first admin
          </Button>
        </FieldGroup>
      </form>
    </Frame>
  )
}

function SignIn({ status, onDone }: { status: TeamStatus; onDone: () => void }) {
  const params = new URLSearchParams(window.location.search)
  const notice =
    params.get("signin") === "expired"
      ? "That sign-in link expired or was used already. Ask for a new one."
      : params.get("signin") === "refused"
        ? (params.get("why") ?? "That sign-in did not work.")
        : null
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [withPassword, setWithPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      if (withPassword) {
        await team.password(email, password)
        onDone()
      } else {
        setSent((await team.link(email)).message)
      }
    } catch (failure) {
      setError(message(failure))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Frame title="Sign in" lead="Your admin invited you with this email.">
      {notice && (
        <Alert>
          <AlertTitle>Not signed in</AlertTitle>
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}
      {sent ? (
        <Alert>
          <MailIcon />
          <AlertTitle>Check your email</AlertTitle>
          <AlertDescription>{sent} It works once, within 15 minutes.</AlertDescription>
        </Alert>
      ) : (
        <form onSubmit={submit}>
          <FieldGroup>
            {status.providers.length > 0 && (
              <>
                <div className="flex flex-col gap-2">
                  {status.providers.map((provider) => (
                    <Button key={provider.name} variant="outline" className="h-10" asChild>
                      <a href={`/auth/${provider.name}/start`}>Continue with {provider.title}</a>
                    </Button>
                  ))}
                </div>
                <FieldSeparator>or</FieldSeparator>
              </>
            )}
            <Field>
              <FieldLabel htmlFor="signin-email">Email</FieldLabel>
              <Input id="signin-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" autoFocus />
            </Field>
            {withPassword && (
              <Field>
                <FieldLabel htmlFor="signin-password">Password</FieldLabel>
                <Input id="signin-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
              </Field>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="h-10" disabled={busy || !email || (withPassword && !password)}>
              {busy ? <Spinner /> : withPassword ? <KeyRoundIcon /> : <MailIcon />}
              {withPassword ? "Sign in" : status.mail ? "Email me a sign-in link" : "Ask for a sign-in link"}
            </Button>
            {!status.mail && !withPassword && (
              <FieldDescription>
                This server sends no email. Your admin can give you a sign-in link from the Team page.
              </FieldDescription>
            )}
            <Button type="button" variant="link" className="h-auto p-0 text-muted-foreground" onClick={() => setWithPassword(!withPassword)}>
              {withPassword ? "Sign in with a link instead" : "I have a password"}
            </Button>
          </FieldGroup>
        </form>
      )}
    </Frame>
  )
}

/** The app shows once someone is signed in; until then, setup or sign-in. */
export function TeamGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<TeamStatus | null>(null)
  const [signed, setSigned] = useState<boolean | null>(null)

  async function load() {
    const found = await team.status()
    setStatus(found)
    setSigned(found.setup_needed ? false : await team.signedIn())
  }

  useEffect(() => {
    load().catch(() => setSigned(false))
  }, [])

  const done = () => window.location.assign("/")
  if (status === null || signed === null) return null
  if (status.setup_needed) return <Setup onDone={done} />
  if (!signed) return <SignIn status={status} onDone={done} />
  return <>{children}</>
}

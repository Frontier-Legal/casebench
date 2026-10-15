// SPDX-License-Identifier: Elastic-2.0
// The admin's page: people and their roles, invitations, API keys for CI, spend limits, and the
// targets casebench.yaml sets (decision 0058).

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { CopyIcon, KeyRoundIcon, MailPlusIcon } from "lucide-react"

import { Section, Status } from "@/components/section"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { ROLES, team, type KeyView, type Limits, type Person, type Targets } from "./api"

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function when(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "Never"
}

function RoleSelect({
  value,
  onChange,
  id,
  roles = ROLES,
}: {
  value: string
  onChange: (role: string) => void
  id?: string
  roles?: readonly string[]
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} size="sm" className="w-32">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {roles.map((role) => (
          <SelectItem key={role} value={role}>
            {role}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function Copyable({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg bg-muted/60 p-3">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate text-xs">{text}</code>
        <Button
          size="icon"
          variant="ghost"
          aria-label="Copy"
          onClick={() => navigator.clipboard?.writeText(text).then(() => toast.success("Copied"))}
        >
          <CopyIcon />
        </Button>
      </div>
    </div>
  )
}

function People() {
  const [people, setPeople] = useState<Person[] | null>(null)
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [role, setRole] = useState("reviewer")
  const [link, setLink] = useState<{ email: string; link: string } | null>(null)

  const load = useCallback(() => team.people().then(setPeople).catch((e) => toast.error(message(e))), [])
  useEffect(() => {
    load()
  }, [load])

  async function invite(event: React.FormEvent) {
    event.preventDefault()
    try {
      const made = await team.invite(email, name, role)
      if (made.link) setLink({ email: made.person.email, link: made.link })
      else toast.success(`A sign-in link is on its way to ${made.person.email}`)
      setEmail("")
      setName("")
      load()
    } catch (failure) {
      toast.error(message(failure))
    }
  }

  async function act(person: Person, action: () => Promise<unknown>, done: string) {
    try {
      const result = await action()
      const made = result as { link?: string | null }
      if (made && "link" in made && made.link) setLink({ email: person.email, link: made.link })
      else toast.success(done)
      load()
    } catch (failure) {
      toast.error(message(failure))
    }
  }

  return (
    <Section title="People" description="Each person signs in with a link to their email, or with Google or Microsoft. Each role includes the one before it.">
      <div className="flex flex-col gap-6">
        <form onSubmit={invite} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto_auto] sm:items-end">
          <Field>
            <FieldLabel htmlFor="invite-email">Email</FieldLabel>
            <Input id="invite-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field>
            <FieldLabel htmlFor="invite-name">Name</FieldLabel>
            <Input id="invite-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field>
            <FieldLabel htmlFor="invite-role">Role</FieldLabel>
            <RoleSelect id="invite-role" value={role} onChange={setRole} />
          </Field>
          <Button type="submit" disabled={!email || !name}>
            <MailPlusIcon /> Invite
          </Button>
        </form>
        {link && <Copyable label={`This server sends no email. Send ${link.email} this link; it works once, within 15 minutes.`} text={link.link} />}
        <Table aria-label="People">
          <TableHeader>
            <TableRow>
              <TableHead>Person</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Last seen</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(people ?? []).map((person) => (
              <TableRow key={person.id}>
                <TableCell>
                  <div className="font-medium">{person.name}</div>
                  <div className="text-xs text-muted-foreground">{person.email}</div>
                </TableCell>
                <TableCell>
                  <RoleSelect
                    value={person.role}
                    onChange={(next) => act(person, () => team.change(person.id, { role: next }), `${person.name} is now ${next}`)}
                  />
                </TableCell>
                <TableCell className="text-sm">
                  {person.active ? when(person.last_seen) : <Status tone="none">Deactivated</Status>}
                </TableCell>
                <TableCell className="text-right whitespace-nowrap">
                  {person.active && (
                    <Button variant="ghost" size="sm" onClick={() => act(person, () => team.newLink(person.id), `A new link is on its way to ${person.email}`)}>
                      New link
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      act(person, () => team.change(person.id, { active: !person.active }), person.active ? `${person.name} can no longer sign in` : `${person.name} can sign in again`)
                    }
                  >
                    {person.active ? "Deactivate" : "Reactivate"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Section>
  )
}

function Keys() {
  const [keys, setKeys] = useState<KeyView[]>([])
  const [name, setName] = useState("")
  const [role, setRole] = useState("engineer")
  const [token, setToken] = useState<string | null>(null)

  const load = useCallback(() => team.keys().then(setKeys).catch((e) => toast.error(message(e))), [])
  useEffect(() => {
    load()
  }, [load])

  async function make(event: React.FormEvent) {
    event.preventDefault()
    try {
      setToken((await team.makeKey(name, role)).token)
      setName("")
      load()
    } catch (failure) {
      toast.error(message(failure))
    }
  }

  return (
    <Section title="API keys" description="For CI and scripts, sent as Authorization: Bearer. A key is shown once.">
      <div className="flex flex-col gap-6">
        <form onSubmit={make} className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
          <Field>
            <FieldLabel htmlFor="key-name">Name</FieldLabel>
            <Input id="key-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="CI" />
          </Field>
          <Field>
            <FieldLabel htmlFor="key-role">Role</FieldLabel>
            <RoleSelect id="key-role" value={role} onChange={setRole} roles={ROLES.filter((r) => r !== "admin")} />
          </Field>
          <Button type="submit" disabled={!name}>
            <KeyRoundIcon /> Create key
          </Button>
        </form>
        {token && <Copyable label="Copy this key now. It is not shown again." text={token} />}
        {keys.length > 0 && (
          <Table aria-label="API keys">
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((key) => (
                <TableRow key={key.id}>
                  <TableCell className="font-medium">{key.name}</TableCell>
                  <TableCell>{key.role}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {when(key.created_at)} by {key.created_by}
                  </TableCell>
                  <TableCell className="text-right">
                    {key.revoked ? (
                      <Status tone="none">Revoked</Status>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => team.revoke(key.id).then(load).catch((e) => toast.error(message(e)))}>
                        Revoke
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </Section>
  )
}

function SpendLimits() {
  const [limits, setLimits] = useState<Limits | null>(null)
  const [teamLimit, setTeamLimit] = useState("")
  const [personLimit, setPersonLimit] = useState("")

  useEffect(() => {
    team
      .limits()
      .then((found) => {
        setLimits(found)
        setTeamLimit(found.team?.toString() ?? "")
        setPersonLimit(found.person?.toString() ?? "")
      })
      .catch((e) => toast.error(message(e)))
  }, [])

  async function save(event: React.FormEvent) {
    event.preventDefault()
    const parse = (text: string) => (text.trim() === "" ? null : Number(text))
    try {
      setLimits(await team.setLimits({ team: parse(teamLimit), person: parse(personLimit) }))
      toast.success("Limits saved")
    } catch (failure) {
      toast.error(message(failure))
    }
  }

  return (
    <Section title="Spend limits" description="What trying questions may cost each day, in US dollars, the agent's and the judge's calls together.">
      <form onSubmit={save} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <Field>
          <FieldLabel htmlFor="limit-team">For the team</FieldLabel>
          <Input id="limit-team" inputMode="decimal" value={teamLimit} onChange={(e) => setTeamLimit(e.target.value)} placeholder="From casebench.yaml" />
        </Field>
        <Field>
          <FieldLabel htmlFor="limit-person">For each person</FieldLabel>
          <Input id="limit-person" inputMode="decimal" value={personLimit} onChange={(e) => setPersonLimit(e.target.value)} placeholder="No limit" />
        </Field>
        <Button type="submit" disabled={limits === null}>
          Save limits
        </Button>
        <FieldDescription className="sm:col-span-3">
          Left empty, the team's limit is casebench.yaml's workbench: try_daily_limit_usd. Limits reset at midnight UTC.
        </FieldDescription>
      </form>
    </Section>
  )
}

function TargetsCard() {
  const [targets, setTargets] = useState<Targets | null>(null)
  useEffect(() => {
    team.targets().then(setTargets).catch(() => {})
  }, [])
  if (!targets) return null
  return (
    <Section title="Targets" description={targets.note}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Copyable label="Target" text={targets.target ? JSON.stringify(targets.target) : "None configured"} />
        <Copyable
          label="The agent's models"
          text={targets.agent_models.map((m) => String(m.model)).join(", ") || "None listed"}
        />
      </div>
    </Section>
  )
}

/** The admin's page. */
export function TeamAdmin() {
  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Team</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Who signs in and with which role, the keys CI uses, and what trying questions may spend.
        </p>
      </div>
      <People />
      <Keys />
      <SpendLimits />
      <TargetsCard />
    </div>
  )
}

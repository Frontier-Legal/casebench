import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"
import { PlusIcon, SearchIcon } from "lucide-react"

import { Status } from "@/components/section"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Spinner } from "@/components/ui/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { api, type CaseDetail, type FormField, type Golden } from "@/lib/api"
import { inputName, taskName } from "@/lib/words"

export interface Opened {
  suite: string
  caseId: string | null
  task?: string
  prefill?: Record<string, string>
}

function fieldLabel(name: string): string {
  const known = inputName(name)
  return known === name ? name.charAt(0).toUpperCase() + name.slice(1) : known
}

const SHORT = new Set(["question", "instruction", "constraints"])

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

/** A case in the form: read, change with a reason, or write anew (decision 0052). */
export function CaseEditor({
  opened,
  tasks,
  locked,
  onClose,
  onSaved,
}: {
  opened: Opened | null
  tasks: string[]
  locked: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const [detail, setDetail] = useState<CaseDetail | null>(null)
  const [fields, setFields] = useState<FormField[] | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [task, setTask] = useState("qa")
  const [reason, setReason] = useState("")
  const [busy, setBusy] = useState(false)
  const creating = opened !== null && opened.caseId === null

  useEffect(() => {
    setDetail(null)
    setFields(null)
    setReason("")
    if (!opened) return
    let live = true
    const load = async () => {
      if (opened.caseId) {
        const found = await api.goldenCase(opened.suite, opened.caseId)
        if (!live) return
        setDetail(found)
        setFields(found.fields)
        setValues(Object.fromEntries(found.fields.map((f) => [f.name, f.value])))
      } else {
        const chosen = opened.task ?? task
        const blank = await api.blankForm(chosen)
        if (!live) return
        setFields(blank)
        setValues(Object.fromEntries(blank.map((f) => [f.name, opened.prefill?.[f.name] ?? ""])))
      }
    }
    load().catch((error) => toast.error(message(error)))
    return () => {
      live = false
    }
    // The task picked for a new case reloads its blank form.
  }, [opened, task]) // eslint-disable-line react-hooks/exhaustive-deps

  const readOnly = locked || (detail !== null && (!detail.editable || detail.waiting !== null))
  const changed =
    detail !== null && detail.fields.some((f) => (values[f.name] ?? "").trim() !== f.value.trim())

  async function save() {
    if (!opened) return
    setBusy(true)
    try {
      const done = creating
        ? await api.createCase(opened.suite, opened.task ?? task, values, reason.trim() || null)
        : await api.proposeChange(opened.suite, opened.caseId!, values, reason)
      toast.success(done.message)
      onSaved()
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Sheet open={opened !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto sm:max-w-2xl">
        <SheetHeader className="border-b">
          <SheetTitle>{creating ? "New case" : (detail?.case_id ?? "Case")}</SheetTitle>
          <SheetDescription>
            {creating
              ? `A draft in ${opened?.suite} until a second editor approves it.`
              : detail
                ? `${taskName(detail.task)} · ${detail.source} · ${detail.approval}${detail.author ? ` · written by ${detail.author}` : ""}`
                : "Loading"}
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-6 p-4">
          {detail?.waiting && (
            <Alert>
              <AlertTitle>
                {detail.waiting.kind === "new" ? "Waiting for approval" : "A change is waiting"}
              </AlertTitle>
              <AlertDescription>
                {detail.waiting.author} {detail.waiting.kind === "new" ? "wrote this case" : "proposed a change"}
                {detail.waiting.reason ? `: “${detail.waiting.reason}”` : ""}. A second editor
                approves it from the review queue.
              </AlertDescription>
            </Alert>
          )}
          {detail && !detail.editable && (
            <Alert>
              <AlertTitle>Changed where it was made</AlertTitle>
              <AlertDescription>
                {taskName(detail.task)} cases come from court decisions and are changed there,
                not in this form.
              </AlertDescription>
            </Alert>
          )}
          {creating && !opened?.task && (
            <Field>
              <FieldLabel>Task</FieldLabel>
              <ToggleGroup
                type="single"
                variant="outline"
                spacing={2}
                value={task}
                onValueChange={(chosen) => chosen && setTask(chosen)}
                className="flex-wrap"
              >
                {tasks
                  .filter((t) => t !== "outcome")
                  .map((t) => (
                    <ToggleGroupItem
                      key={t}
                      value={t}
                      className="data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
                    >
                      {taskName(t)}
                    </ToggleGroupItem>
                  ))}
              </ToggleGroup>
            </Field>
          )}
          {!fields ? (
            <div className="flex flex-col gap-4">
              <Skeleton className="h-16" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
          ) : (
            <FieldGroup>
              {fields.map((field) => (
                <Field key={field.name}>
                  <FieldLabel htmlFor={`field-${field.name}`}>{fieldLabel(field.name)}</FieldLabel>
                  {SHORT.has(field.name) ? (
                    <Textarea
                      id={`field-${field.name}`}
                      rows={2}
                      readOnly={readOnly}
                      value={values[field.name] ?? ""}
                      onChange={(event) => setValues((now) => ({ ...now, [field.name]: event.target.value }))}
                    />
                  ) : (
                    <Textarea
                      id={`field-${field.name}`}
                      rows={field.name === "key points" ? 5 : 4}
                      readOnly={readOnly}
                      className={field.name === "key points" ? "font-mono text-[0.8rem]" : undefined}
                      value={values[field.name] ?? ""}
                      onChange={(event) => setValues((now) => ({ ...now, [field.name]: event.target.value }))}
                    />
                  )}
                  {field.help && <FieldDescription>{field.help}</FieldDescription>}
                </Field>
              ))}
              {!readOnly && (
                <Field>
                  <FieldLabel htmlFor="field-reason">
                    {creating ? "A note for the second editor" : "Why do you change it?"}
                  </FieldLabel>
                  <Input
                    id="field-reason"
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder={creating ? "Optional" : "For example: statute amended in 2025"}
                  />
                  <FieldDescription>
                    {creating
                      ? "The case joins its suite as a draft."
                      : "Required. The second editor sees it beside the change."}
                  </FieldDescription>
                </Field>
              )}
            </FieldGroup>
          )}
        </div>
        {!readOnly && (
          <SheetFooter className="mt-auto flex-row justify-end border-t bg-muted/50">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={save}
              disabled={busy || !fields || (!creating && (!changed || !reason.trim()))}
            >
              {busy && <Spinner />}
              {creating ? "Save as draft" : "Propose the change"}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  )
}

/** The answer key every score rests on, per suite (decision 0052). */
export function GoldenData({
  locked,
  opened,
  onOpen,
  onChanged,
}: {
  locked: boolean
  opened: Opened | null
  onOpen: (opened: Opened | null) => void
  onChanged: () => void
}) {
  const [golden, setGolden] = useState<Golden | null>(null)
  const [suite, setSuite] = useState<string | null>(null)
  const [query, setQuery] = useState("")

  const load = useCallback(async () => {
    const found = await api.golden()
    setGolden(found)
    setSuite((now) => now ?? found.suites[0]?.suite_id ?? null)
  }, [])

  useEffect(() => {
    load().catch((error) => toast.error(message(error)))
  }, [load])

  const cases = useMemo(() => {
    const listed = golden?.suites.find((s) => s.suite_id === suite)?.cases ?? []
    const words = query.trim().toLocaleLowerCase()
    return words
      ? listed.filter((c) => `${c.case_id} ${c.title}`.toLocaleLowerCase().includes(words))
      : listed
  }, [golden, suite, query])

  const counts = useMemo(() => {
    const listed = golden?.suites.find((s) => s.suite_id === suite)?.cases ?? []
    return {
      approved: listed.filter((c) => c.approval === "approved").length,
      draft: listed.filter((c) => c.approval === "draft").length,
      waiting: listed.filter((c) => c.waiting).length,
    }
  }, [golden, suite])

  if (!golden) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Golden data</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            The answer key every score rests on. A change takes effect only when a second
            editor approves it.
          </p>
        </div>
        {!locked && suite && (
          <Button onClick={() => onOpen({ suite, caseId: null })}>
            <PlusIcon /> New case
          </Button>
        )}
      </div>
      {golden.suites.length === 0 ? (
        <Empty className="border">
          <EmptyHeader>
            <EmptyTitle>No suites here</EmptyTitle>
            <EmptyDescription>
              Start the workbench where your suites are, or name them with casebench ui --suites.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <Card className="gap-4">
          <CardHeader>
            <CardTitle>{suite}</CardTitle>
            <CardDescription>
              {counts.approved} approved · {counts.draft} drafts
              {counts.waiting ? ` · ${counts.waiting} waiting for a second editor` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {golden.suites.length > 1 && (
                <Tabs value={suite ?? undefined} onValueChange={setSuite}>
                  <TabsList>
                    {golden.suites.map((s) => (
                      <TabsTrigger key={s.suite_id} value={s.suite_id}>
                        {s.suite_id}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              )}
              <div className="relative sm:w-72">
                <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  aria-label="Search cases"
                  placeholder="Search cases"
                  className="pl-8"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="hidden w-36 md:table-cell">Case</TableHead>
                    <TableHead>Question</TableHead>
                    <TableHead className="hidden md:table-cell">Task</TableHead>
                    <TableHead className="hidden md:table-cell">Source</TableHead>
                    <TableHead className="hidden text-right md:table-cell">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cases.map((row) => (
                    <TableRow
                      key={row.case_id}
                      className="cursor-pointer"
                      onClick={() => onOpen({ suite: suite!, caseId: row.case_id })}
                    >
                      <TableCell className="hidden font-mono text-xs md:table-cell">{row.case_id}</TableCell>
                      <TableCell className="max-w-md whitespace-normal md:truncate md:whitespace-nowrap">
                        <div className="line-clamp-2 md:line-clamp-none">{row.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground md:hidden">
                          <span className="font-mono">{row.case_id}</span>
                          <Status tone={row.approval === "approved" ? "good" : "warn"}>
                            {row.approval === "approved" ? "Approved" : "Draft"}
                          </Status>
                          {row.waiting && <Badge variant="outline">Waiting</Badge>}
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">{taskName(row.task)}</TableCell>
                      <TableCell className="hidden capitalize md:table-cell">{row.source}</TableCell>
                      <TableCell className="hidden text-right md:table-cell">
                        <span className="inline-flex items-center gap-2">
                          {row.waiting && <Badge variant="outline">Waiting</Badge>}
                          <Status tone={row.approval === "approved" ? "good" : "warn"}>
                            {row.approval === "approved" ? "Approved" : "Draft"}
                          </Status>
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                  {cases.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                        No case matches.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
      <CaseEditor
        opened={opened}
        tasks={golden.tasks}
        locked={locked}
        onClose={() => onOpen(null)}
        onSaved={() => {
          onOpen(null)
          load().catch((error) => toast.error(message(error)))
          onChanged()
        }}
      />
    </div>
  )
}

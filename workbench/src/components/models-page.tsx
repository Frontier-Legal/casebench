// The Models page: each model Casebench calls itself, what it is for, and a way to change it,
// test it and set its key, for a judge, a second judge and the two extraction models (0065).

import { useState } from "react"
import { toast } from "sonner"
import { BookOpenTextIcon, GavelIcon, ScanSearchIcon, ScaleIcon } from "lucide-react"

import { Section } from "@/components/section"
import type { ModelBlock } from "@/components/settings/model-editor"
import { EmptyRole, ModelCard } from "@/components/setup/model-card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { agentModelsFromCode, message, useSettings, type Settings } from "@/lib/use-settings"

type Extract = { models: ModelBlock[] }

function RoleTitle({ icon: Icon, children }: { icon: React.ElementType; children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-2">
      <Icon className="size-4 text-primary" /> {children}
    </span>
  )
}

export function JudgeRoles({ settings, second = true }: { settings: Settings; second?: boolean }) {
  const { view, setView, save } = settings
  if (!view) return null
  const judges = (view.sections.judges as ModelBlock[] | undefined) ?? []
  const [first, other] = [view.models.find((m) => m.role === "judge"), view.models.find((m) => m.role === "second judge")]
  return (
    <div className="flex flex-col gap-4">
      {first && judges[0] ? (
        <ModelCard
          title="The judge"
          view={view}
          model={first}
          block={judges[0]}
          onView={setView}
          onChange={(block) => save("judges", [block, ...judges.slice(1)])}
        />
      ) : (
        <EmptyRole
          title="The judge"
          text="No judge yet. Without one, Casebench scores rulings only: citations and criteria wait for a judge."
          action="Choose the judge"
          onPicked={(block) => save("judges", [block])}
        />
      )}
      {second && judges[0] && (
        <div className="flex flex-col gap-2">
          <div className="text-sm font-medium">Second judge</div>
          {other && judges[1] ? (
            <ModelCard
              title="Second judge"
              view={view}
              model={other}
              block={judges[1]}
              onView={setView}
              onChange={(block) => save("judges", [judges[0], block])}
              onRemove={() => save("judges", [judges[0]])}
            />
          ) : (
            <EmptyRole
              title="Second judge"
              text={`Optional. A model from another family than ${first?.family ?? "the judge's"} judges every answer again; where the two disagree, the answer goes to a lawyer first.`}
              action="Add a second judge"
              onPicked={(block) => save("judges", [judges[0], block])}
            />
          )}
        </div>
      )}
    </div>
  )
}

function ExtractionRoles({ settings }: { settings: Settings }) {
  const { view, setView, save } = settings
  const [pending, setPending] = useState<ModelBlock | null>(null)
  if (!view) return null
  const pair = ((view.sections.extract as Extract | undefined)?.models ?? []).slice(0, 2)
  const shown = view.models.filter((m) => m.role.startsWith("extraction"))
  async function pick(index: number, block: ModelBlock) {
    if (pair.length === 2) {
      await save("extract", { models: pair.map((m, i) => (i === index ? block : m)) })
    } else if (pending) {
      if (await save("extract", { models: [pending, block] })) setPending(null)
    } else {
      setPending(block)
    }
  }
  if (pair.length === 2 && shown.length === 2) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {shown.map((model, index) => (
          <ModelCard
            key={model.role}
            title={`Reader ${index + 1}`}
            view={view}
            model={model}
            block={pair[index]}
            onView={setView}
            onChange={(block) => pick(index, block)}
            onRemove={index === 1 ? () => save("extract", null) : undefined}
          />
        ))}
      </div>
    )
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {pending ? (
        <div aria-label="Reader 1" className="flex flex-col gap-1 rounded-xl border bg-card p-4">
          <span className="font-mono text-sm font-medium">{pending.model}</span>
          <span className="text-xs text-muted-foreground">
            {pending.provider} · saved once the second reader is chosen
          </span>
        </div>
      ) : (
        <EmptyRole
          title="Reader 1"
          text="The first of two models that read each court decision."
          action="Choose reader 1"
          onPicked={(block) => pick(0, block)}
        />
      )}
      <EmptyRole
        title="Reader 2"
        text="A different model; only what both readers find becomes a case."
        action="Choose reader 2"
        onPicked={(block) => (pending ? pick(1, block) : setPending(block))}
      />
    </div>
  )
}

function ReadFromCode({ settings, again }: { settings: Settings; again: boolean }) {
  const [busy, setBusy] = useState(false)
  async function read() {
    setBusy(true)
    try {
      const found = await agentModelsFromCode()
      if (!found.length) {
        toast.info("No model the catalog knows is named in your agent's code")
        return
      }
      if (await settings.save("agent_models", found)) {
        toast.success(`${found.length} ${found.length === 1 ? "model" : "models"} read from your code`)
      }
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Button variant="outline" size="sm" onClick={read} disabled={busy}>
      {busy ? <Spinner /> : <ScanSearchIcon />} {again ? "Read them again" : "Read them from your code"}
    </Button>
  )
}

export function ModelsPage() {
  const settings = useSettings()
  const view = settings.view
  if (!view) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    )
  }
  const agentModels =
    (view.sections.agent_models as { model: string; family?: string; price?: { input: number; output: number } }[]) ??
    []
  return (
    <div className="flex flex-col gap-6 pb-10">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight md:text-2xl">Models</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          The models Casebench calls itself to grade your agent. Change one by picking it from the public model
          catalog; its price and limits come with it. Your agent's own models are what is measured, and are listed
          last.
        </p>
      </div>
      <Section
        title={(<RoleTitle icon={GavelIcon}>The judge</RoleTitle>)}
        description="Finds each authority an answer cites, matches it to your sources and checks that it says what the answer claims. It also grades criteria lawyers wrote."
        action={<Badge>Needed for citations</Badge>}
      >
        <JudgeRoles settings={settings} />
      </Section>
      <Section
        title={(<RoleTitle icon={BookOpenTextIcon}>Extraction models</RoleTitle>)}
        description="Two different models read your court decisions and write test cases from them: the ruling, the statutes and the precedents. A field becomes a case only when both agree."
        action={<Badge variant="secondary">Optional</Badge>}
      >
        <ExtractionRoles settings={settings} />
      </Section>
      <Section
        title={(<RoleTitle icon={ScaleIcon}>Your agent's models</RoleTitle>)}
        description="What your agent calls, with the price a run uses to say what it spent. A judge of the same family would favour their answers, so a run warns."
        action={<ReadFromCode settings={settings} again={agentModels.length > 0} />}
      >
        {agentModels.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Model</TableHead>
                <TableHead>Family</TableHead>
                <TableHead className="text-right">Price per million tokens</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agentModels.map((m) => (
                <TableRow key={m.model}>
                  <TableCell className="font-mono text-xs">{m.model}</TableCell>
                  <TableCell>{m.family ?? "–"}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {m.price ? `$${m.price.input} in · $${m.price.output} out` : "–"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-sm text-muted-foreground">
            None listed yet. Read them from your agent's code: each model the public catalog knows comes with its
            family and price. Settings, under Agent, adds one by hand.
          </p>
        )}
      </Section>
      {settings.asking}
    </div>
  )
}

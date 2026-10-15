import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { CircleCheckBigIcon, CircleHelpIcon } from "lucide-react"

import { AppSidebar, type Page } from "@/components/app-sidebar"
import { ChangeReview } from "@/components/change-review"
import { GoldenData, type Opened } from "@/components/golden-data"
import { CompareRuns } from "@/components/compare-runs"
import { Reports } from "@/components/reports"
import { TryQuestion } from "@/components/try-question"
import { AnswerReview } from "@/components/answer-review"
import { DraftReview } from "@/components/draft-review"
import { ItemHeader } from "@/components/item-header"
import { ShortcutsDialog } from "@/components/shortcuts-dialog"
import { Welcome } from "@/components/welcome"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { SidebarInset, SidebarProvider, SidebarTrigger, useSidebar } from "@/components/ui/sidebar"
import { Skeleton } from "@/components/ui/skeleton"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  ApiError,
  api,
  storeName,
  storedName,
  type GivenFact,
  type GivenVerdict,
  type Item,
  type Me,
  type QueueItem,
  type View,
} from "@/lib/api"
import { useShortcuts } from "@/lib/keys"
import { plural } from "@/lib/words"

// An open item's reservation is renewed this often; it lapses after 15 minutes.
const RENEW_MS = 5 * 60 * 1000

function useDarkMode() {
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)")
    if (!media) return
    const apply = () => document.documentElement.classList.toggle("dark", media.matches)
    apply()
    media.addEventListener?.("change", apply)
    return () => media.removeEventListener?.("change", apply)
  }, [])
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

const PAGES: Record<Page, string> = {
  queue: "Review queue",
  golden: "Golden data",
  try: "Try a question",
  compare: "Compare runs",
  reports: "Reports",
}

const CRUMBS: Record<Item["kind"], string> = {
  answer: "Answer",
  draft: "Court draft",
  change: "Change to approve",
}

function TopBar({
  page,
  item,
  done,
  left,
  onHelp,
}: {
  page: Page
  item: Item | null
  done: number
  left: number
  onHelp: () => void
}) {
  const total = done + left
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/90 px-3 backdrop-blur md:px-4">
      <SidebarTrigger aria-label="Open the queue" />
      <Separator orientation="vertical" className="mx-1 h-5" />
      <Breadcrumb className="min-w-0 flex-1">
        <BreadcrumbList className="flex-nowrap">
          {page !== "queue" ? (
            <BreadcrumbItem>
              <BreadcrumbPage>{PAGES[page]}</BreadcrumbPage>
            </BreadcrumbItem>
          ) : (
            <>
              <BreadcrumbItem className="hidden sm:inline-flex">Review queue</BreadcrumbItem>
              {item && <BreadcrumbSeparator className="hidden sm:inline-flex" />}
              {item && (
                <BreadcrumbItem className="min-w-0">
                  <BreadcrumbPage className="truncate">
                    {CRUMBS[item.kind]} · {item.where}
                  </BreadcrumbPage>
                </BreadcrumbItem>
              )}
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>
      <div className="hidden items-center gap-3 md:flex" aria-label="Progress this session">
        <span className="text-xs whitespace-nowrap text-muted-foreground tabular-nums">
          {done} done · {left} to do
        </span>
        <Progress value={total ? (done / total) * 100 : 0} className="w-28" />
      </div>
      <Button variant="ghost" size="icon" onClick={onHelp} aria-label="Keyboard shortcuts">
        <CircleHelpIcon />
      </Button>
    </header>
  )
}

function Workbench({ me, onMe, onLeave }: { me: Me; onMe: (me: Me) => void; onLeave: () => void }) {
  const [queue, setQueue] = useState<QueueItem[] | null>(null)
  const [item, setItem] = useState<Item | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [help, setHelp] = useState(false)
  const [done, setDone] = useState(0)
  const [page, setPage] = useState<Page>("queue")
  const [opened, setOpened] = useState<Opened | null>(null)
  const skipped = useRef<Set<string>>(new Set())
  const { isMobile, setOpenMobile } = useSidebar()
  const mobile = useRef(isMobile)
  mobile.current = isMobile

  const open = useCallback(
    async (key: string) => {
      setLoading(true)
      setPage("queue")
      if (mobile.current) setOpenMobile(false)
      try {
        await api.reserve(key)
        setItem(await api.item(key))
        window.scrollTo?.({ top: 0 })
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          toast.info(error.message)
          skipped.current.add(key)
        } else {
          toast.error(message(error))
        }
        setItem(null)
      } finally {
        setLoading(false)
      }
    },
    [setOpenMobile],
  )

  const next = useCallback(
    async (after?: string) => {
      const { items } = await api.queue()
      setQueue(items)
      const first = items.find((i) => i.key !== after && !skipped.current.has(i.key))
      if (first) await open(first.key)
      else setItem(null)
    },
    [open],
  )

  useEffect(() => {
    next().catch((error) => toast.error(message(error)))
  }, [next])

  useEffect(() => {
    if (!item) return
    const timer = window.setInterval(() => api.reserve(item.key).catch(() => {}), RENEW_MS)
    return () => window.clearInterval(timer)
  }, [item])

  useShortcuts({ help: () => setHelp(true) }, item === null || page !== "queue")

  async function finish(send: () => Promise<{ message: string }>) {
    if (!item) return
    setBusy(true)
    try {
      const finished = await send()
      toast.success(finished.message)
      setDone((n) => n + 1)
      await next(item.key)
    } catch (error) {
      toast.error(message(error))
    } finally {
      setBusy(false)
    }
  }

  const saveDraft = (payload: Record<string, unknown>) => {
    if (item) api.saveDraft(item.key, payload).catch(() => {})
  }

  async function switchView(view: View) {
    try {
      onMe(await api.saveMe(me.name, view))
      if (item) setItem(await api.item(item.key))
    } catch (error) {
      toast.error(message(error))
    }
  }

  const left = queue?.length ?? 0
  let body: React.ReactNode
  if (page === "try") {
    body = <TryQuestion locked={me.role_locked} />
  } else if (page === "compare") {
    body = <CompareRuns onHelp={() => setHelp(true)} />
  } else if (page === "reports") {
    body = <Reports onOpen={open} />
  } else if (page === "golden") {
    body = (
      <GoldenData
        locked={me.role_locked}
        opened={opened}
        onOpen={setOpened}
        onChanged={() => api.queue().then(({ items }) => setQueue(items)).catch(() => {})}
      />
    )
  } else if (queue === null || (loading && !item)) {
    body = (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-8 w-2/3" />
        <div className="grid gap-3 sm:grid-cols-3">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    )
  } else if (!item) {
    body = (
      <Empty className="mt-10 border md:mt-20">
        <EmptyHeader>
          <EmptyMedia variant="icon" className="bg-success/12 text-success">
            <CircleCheckBigIcon />
          </EmptyMedia>
          <EmptyTitle>{done ? "All caught up" : "Nothing to review"}</EmptyTitle>
          <EmptyDescription>
            {done
              ? `You finished ${plural(done, "item")} this session. New answers and court drafts appear here when your team runs the AI again.`
              : me.view === "engineering"
                ? "Run a suite with casebench run, or generate court cases with casebench generate. Answers to review and court drafts to approve appear here."
                : "When your team runs the AI on new cases, its answers and new court drafts appear here."}
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button variant="outline" onClick={() => next().catch((e) => toast.error(message(e)))}>
            Check again
          </Button>
        </EmptyContent>
      </Empty>
    )
  } else {
    body = (
      <div key={item.key} className="flex flex-col gap-6">
        <ItemHeader item={item} />
        {item.kind === "answer" ? (
          <AnswerReview
            item={item}
            left={left}
            busy={busy}
            onDraft={saveDraft}
            onHelp={() => setHelp(true)}
            onFinish={(verdicts: GivenVerdict[]) => finish(() => api.finishAnswer(item.key, verdicts))}
          />
        ) : item.kind === "change" ? (
          <ChangeReview
            item={item}
            left={left}
            busy={busy}
            onDraft={saveDraft}
            onHelp={() => setHelp(true)}
            onFinish={(decision, note) => finish(() => api.finishChange(item.key, decision, note))}
          />
        ) : (
          <DraftReview
            item={item}
            left={left}
            busy={busy}
            onDraft={saveDraft}
            onHelp={() => setHelp(true)}
            onFinish={(facts: GivenFact[]) => finish(() => api.finishDraft(item.key, facts))}
          />
        )}
      </div>
    )
  }

  return (
    <>
      <AppSidebar
        me={me}
        page={page}
        onPage={(chosen) => {
          setPage(chosen)
          if (mobile.current) setOpenMobile(false)
        }}
        items={queue}
        current={item?.key ?? null}
        onPick={open}
        onView={switchView}
        onHelp={() => setHelp(true)}
        onLeave={onLeave}
      />
      <SidebarInset className="min-w-0">
        <TopBar page={page} item={item} done={done} left={left} onHelp={() => setHelp(true)} />
        <main className="mx-auto flex w-full max-w-[96rem] flex-1 flex-col px-4 pt-6 md:px-6">
          {body}
        </main>
      </SidebarInset>
      <ShortcutsDialog open={help} onOpenChange={setHelp} />
    </>
  )
}

export function App() {
  useDarkMode()
  const [roleLocked, setRoleLocked] = useState(false)
  const [me, setMe] = useState<Me | null | undefined>(undefined)

  useEffect(() => {
    let live = true
    async function load() {
      const session = await api.session()
      if (!live) return
      setRoleLocked(session.role_locked)
      if (!storedName()) return setMe(null)
      try {
        const found = await api.me()
        if (live) setMe(found)
      } catch {
        if (live) setMe(null)
      }
    }
    load().catch(() => live && setMe(null))
    return () => {
      live = false
    }
  }, [])

  async function start(name: string, view: View) {
    storeName(name)
    setMe(await api.saveMe(name, view))
  }

  return (
    <TooltipProvider>
      {me === undefined ? null : me === null ? (
        <Welcome roleLocked={roleLocked} onStart={start} />
      ) : (
        <SidebarProvider style={{ "--sidebar-width": "20rem" } as React.CSSProperties}>
          <Workbench
            me={me}
            onMe={setMe}
            onLeave={() => {
              storeName(null)
              setMe(null)
            }}
          />
        </SidebarProvider>
      )}
      <Toaster position="top-right" offset={{ top: 64, right: 16 }} richColors closeButton />
    </TooltipProvider>
  )
}

import { useState } from "react"
import {
  ChartColumnIcon,
  ChevronsUpDownIcon,
  CodeIcon,
  DatabaseIcon,
  FileCheckIcon,
  FilePenIcon,
  GitCompareArrowsIcon,
  InboxIcon,
  MessageCircleQuestionIcon,
  KeyboardIcon,
  LogOutIcon,
  MessageSquareTextIcon,
  ScaleIcon,
} from "lucide-react"

import { Status } from "@/components/section"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { Me, QueueItem, View } from "@/lib/api"

type Filter = "all" | "answer" | "approve"
export type Page = "queue" | "golden" | "try" | "compare" | "reports"

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase()
}

const KINDS: Record<QueueItem["kind"], string> = {
  answer: "Answer",
  draft: "Court draft",
  change: "Change to approve",
}

function Flag({ flag }: { flag: string }) {
  return (
    <Status tone={flag === "failed" ? "bad" : flag === "judges disagreed" ? "warn" : "none"}>
      {flag}
    </Status>
  )
}

/** The queue down the side, the open item marked, and who is working. */
export function AppSidebar({
  me,
  page,
  onPage,
  items,
  current,
  onPick,
  onView,
  onHelp,
  onLeave,
}: {
  me: Me
  page: Page
  onPage: (page: Page) => void
  items: QueueItem[] | null
  current: string | null
  onPick: (key: string) => void
  onView: (view: View) => void
  onHelp: () => void
  onLeave: () => void
}) {
  const [filter, setFilter] = useState<Filter>("all")
  const fits = (item: QueueItem, kind: Filter) =>
    kind === "all" || (kind === "answer" ? item.kind === "answer" : item.kind !== "answer")
  const shown = (items ?? []).filter((item) => fits(item, filter))
  const count = (kind: Filter) => (items ?? []).filter((item) => fits(item, kind)).length

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="gap-3 px-3 pt-4">
        <div className="flex items-center gap-2.5 px-1">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ScaleIcon className="size-4.5" />
          </div>
          <div className="leading-tight">
            <div className="font-semibold tracking-tight">Casebench</div>
            <div className="text-xs text-muted-foreground">Workbench</div>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu aria-label="Pages">
              <SidebarMenuItem>
                <SidebarMenuButton isActive={page === "queue"} onClick={() => onPage("queue")}>
                  <InboxIcon /> Review queue
                </SidebarMenuButton>
                <SidebarMenuBadge>{items?.length ?? ""}</SidebarMenuBadge>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={page === "golden"} onClick={() => onPage("golden")}>
                  <DatabaseIcon /> Golden data
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={page === "try"} onClick={() => onPage("try")}>
                  <MessageCircleQuestionIcon /> Try a question
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={page === "compare"} onClick={() => onPage("compare")}>
                  <GitCompareArrowsIcon /> Compare runs
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton isActive={page === "reports"} onClick={() => onPage("reports")}>
                  <ChartColumnIcon /> Reports
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        {page === "queue" && (
        <SidebarGroup>
          <SidebarGroupLabel>To do</SidebarGroupLabel>
          <Tabs value={filter} onValueChange={(value) => setFilter(value as Filter)} className="mb-2 px-1">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="all" className="text-xs">
                All <span className="text-muted-foreground tabular-nums">{count("all")}</span>
              </TabsTrigger>
              <TabsTrigger value="answer" className="text-xs">
                Answers <span className="text-muted-foreground tabular-nums">{count("answer")}</span>
              </TabsTrigger>
              <TabsTrigger value="approve" className="text-xs">
                Approvals <span className="text-muted-foreground tabular-nums">{count("approve")}</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <SidebarGroupContent>
            <SidebarMenu aria-label="Queue">
              {items === null &&
                Array.from({ length: 6 }, (_, n) => (
                  <SidebarMenuItem key={n}>
                    <SidebarMenuSkeleton showIcon />
                  </SidebarMenuItem>
                ))}
              {items !== null && shown.length === 0 && (
                <p className="px-2 py-6 text-center text-sm text-muted-foreground">Nothing here.</p>
              )}
              {shown.map((item) => (
                <SidebarMenuItem key={item.key}>
                  <SidebarMenuButton
                    isActive={item.key === current}
                    onClick={() => onPick(item.key)}
                    className="h-auto items-start gap-2.5 py-2"
                  >
                    {item.kind === "draft" ? (
                      <FileCheckIcon className="mt-0.5 text-muted-foreground" />
                    ) : item.kind === "change" ? (
                      <FilePenIcon className="mt-0.5 text-muted-foreground" />
                    ) : (
                      <MessageSquareTextIcon className="mt-0.5 text-muted-foreground" />
                    )}
                    <div className="flex min-w-0 flex-col gap-1">
                      <span className="line-clamp-2 leading-snug">{item.title}</span>
                      <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                        {item.flags.includes("new case") ? "New case to approve" : KINDS[item.kind]} ·{" "}
                        {item.where}
                        {item.flags
                          .filter((flag) => !["court draft", "change", "new case"].includes(flag))
                          .map((flag) => (
                            <Flag key={flag} flag={flag} />
                          ))}
                      </span>
                    </div>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" aria-label={`${me.name}: account and view`}>
                  <Avatar className="size-8 rounded-lg">
                    <AvatarFallback className="rounded-lg">
                      {initials(me.name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left leading-tight">
                    <span className="truncate font-medium">{me.name}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {me.view === "engineering" ? "Engineering view" : "Review view"}
                    </span>
                  </div>
                  <ChevronsUpDownIcon className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-64">
                <DropdownMenuLabel>Signed in as {me.name}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                {!me.role_locked && (
                  <>
                    <DropdownMenuRadioGroup
                      value={me.view}
                      onValueChange={(value) => onView(value as View)}
                    >
                      <DropdownMenuRadioItem value="review">
                        <ScaleIcon /> Review view
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="engineering">
                        <CodeIcon /> Engineering view
                      </DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem onSelect={onHelp}>
                  <KeyboardIcon /> Keyboard shortcuts
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={onLeave}>
                  <LogOutIcon /> Not {me.name}? Switch person
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}

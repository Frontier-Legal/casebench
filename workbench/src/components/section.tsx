import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { cn } from "@/lib/utils"

/** A card with a title, a line saying what it holds, its content and an optional footer. */
export function Section({
  title,
  description,
  action,
  footer,
  children,
  className,
  ...props
}: {
  title: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  footer?: React.ReactNode
  children: React.ReactNode
  className?: string
} & Omit<React.ComponentProps<"div">, "title">) {
  return (
    <Card className={cn("gap-4", footer && "pb-0", className)} {...props}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        {action && <CardAction>{action}</CardAction>}
      </CardHeader>
      <CardContent>{children}</CardContent>
      {footer && <CardFooter className="border-t bg-muted/50 py-4">{footer}</CardFooter>}
    </Card>
  )
}

/** A small capitalised label above a value. */
export function Overline({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("text-xs font-medium tracking-wide text-muted-foreground uppercase", className)}>
      {children}
    </div>
  )
}

/** A quiet box inside a card: a label, a value and a line under it. */
export function Tile({
  label,
  value,
  caption,
  className,
}: {
  label: string
  value: React.ReactNode
  caption?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1 rounded-lg bg-muted/50 p-3", className)}>
      <Overline>{label}</Overline>
      <div className="truncate text-base font-semibold tracking-tight sm:text-lg">{value}</div>
      {caption && <div className="truncate text-xs text-muted-foreground">{caption}</div>}
    </div>
  )
}

const DOTS = {
  good: "bg-success",
  bad: "bg-destructive",
  warn: "bg-warning",
  none: "bg-muted-foreground/50",
}

/** A coloured dot before a word, for a state. */
export function Status({
  tone,
  children,
  className,
}: {
  tone: keyof typeof DOTS
  children: React.ReactNode
  className?: string
}) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", className)}>
      <span aria-hidden className={cn("size-1.5 shrink-0 rounded-full", DOTS[tone])} />
      {children}
    </span>
  )
}

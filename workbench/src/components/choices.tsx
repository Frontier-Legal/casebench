import { Kbd } from "@/components/ui/kbd"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export interface Choice<T extends string> {
  value: T
  label: string
  icon?: React.ComponentType<{ className?: string }>
}

/** Numbered choices for one row: the digit picks it when the row is highlighted, a tap or a
 * click picks it anywhere. */
export function Choices<T extends string>({
  choices,
  value,
  onChoose,
  label,
}: {
  choices: Choice<T>[]
  value: T | null
  onChoose: (value: T) => void
  label: string
}) {
  return (
    <ToggleGroup
      type="single"
      variant="outline"
      spacing={2}
      aria-label={label}
      value={value ?? ""}
      onValueChange={(chosen) => chosen && onChoose(chosen as T)}
      onClick={(event) => event.stopPropagation()}
      className="w-full sm:w-auto"
    >
      {choices.map((choice, index) => (
        <ToggleGroupItem
          key={choice.value}
          value={choice.value}
          aria-label={choice.label}
          className="h-10 flex-1 gap-1.5 bg-background px-3 data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground sm:h-8 sm:flex-none"
        >
          {choice.icon && <choice.icon />}
          {choice.label}
          <Kbd className="ml-0.5 hidden in-data-[state=on]:bg-primary-foreground/15 in-data-[state=on]:text-primary-foreground md:inline-flex">
            {index + 1}
          </Kbd>
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  )
}

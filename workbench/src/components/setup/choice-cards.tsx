// A choice among a few options, each a card with a title and a line: shadcn's radio group with
// field labels, as the welcome screen asks what a person does (decision 0065).

import { useId } from "react"

import {
  Field,
  FieldContent,
  FieldDescription,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { cn } from "@/lib/utils"

export type Choice = {
  value: string
  title: React.ReactNode
  text?: React.ReactNode
  icon?: React.ElementType
}

export function ChoiceCards({
  label,
  value,
  choices,
  onChange,
  className,
}: {
  label: string
  value: string | null
  choices: Choice[]
  onChange: (value: string) => void
  className?: string
}) {
  const id = useId()
  return (
    <RadioGroup aria-label={label} value={value ?? ""} onValueChange={onChange} className={cn("grid gap-3", className)}>
      {choices.map((choice) => (
        <FieldLabel key={choice.value} htmlFor={`${id}-${choice.value}`}>
          <Field orientation="horizontal">
            {choice.icon && <choice.icon className="size-4 text-muted-foreground" />}
            <FieldContent>
              <FieldTitle>{choice.title}</FieldTitle>
              {choice.text && <FieldDescription>{choice.text}</FieldDescription>}
            </FieldContent>
            <RadioGroupItem value={choice.value} id={`${id}-${choice.value}`} />
          </Field>
        </FieldLabel>
      ))}
    </RadioGroup>
  )
}

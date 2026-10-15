import { Section } from "@/components/section"
import type { Input } from "@/lib/api"
import { inputName } from "@/lib/words"

/** What the AI was asked, as the case gives it. */
export function InputsCard({
  inputs,
  title = "What the AI was asked",
}: {
  inputs: Input[]
  title?: string
}) {
  if (!inputs.length) return null
  return (
    <Section title={title}>
      <dl className="flex flex-col gap-4">
        {inputs.map((input) => (
          <div key={input.name} className="flex flex-col gap-1">
            <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {inputName(input.name)}
            </dt>
            <dd className="max-h-72 overflow-auto text-sm leading-relaxed whitespace-pre-wrap">
              {input.text}
            </dd>
          </div>
        ))}
      </dl>
    </Section>
  )
}

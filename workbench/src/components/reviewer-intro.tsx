// Shown once to a person who has just named themselves as a reviewer: how a review works, in
// three short pictures of the screen they are about to use (decision 0065).

import { useState } from "react"
import { BookOpenCheckIcon, KeyboardIcon, ShieldCheckIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Kbd } from "@/components/ui/kbd"
import { cn } from "@/lib/utils"

const SLIDES = [
  {
    icon: BookOpenCheckIcon,
    title: "The evidence is beside every answer",
    text: "On the left, what the court decided or what your colleague wrote. On the right, the AI's answer, each citation underlined: green when the source says it, orange when it does not, red when the source does not exist.",
  },
  {
    icon: KeyboardIcon,
    title: "The judge's view is filled in",
    text: "A model has already marked each point pass or fail. Keep its view, or change it and say why.",
    keys: ["1", "2", "Ctrl", "Enter"],
  },
  {
    icon: ShieldCheckIcon,
    title: "Your decision always wins",
    text: "Each verdict is saved under your name. Where you overrule the judge, your verdict is the one the report counts.",
  },
]

export function ReviewerIntro({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [slide, setSlide] = useState(0)
  const shown = SLIDES[slide]
  const last = slide === SLIDES.length - 1
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <div className="flex size-12 items-center justify-center rounded-xl bg-brand-soft text-primary">
          <shown.icon className="size-6" />
        </div>
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl font-medium">{shown.title}</DialogTitle>
          <DialogDescription className="text-base">{shown.text}</DialogDescription>
        </DialogHeader>
        {shown.keys && (
          <p className="flex flex-wrap items-center gap-1.5 text-sm text-muted-foreground">
            <Kbd>1</Kbd> pass, <Kbd>2</Kbd> fail, and <Kbd>Ctrl</Kbd>
            <Kbd>Enter</Kbd> to finish and open the next answer.
          </p>
        )}
        <DialogFooter className="items-center sm:justify-between">
          <div aria-hidden className="flex gap-1.5">
            {SLIDES.map((item, n) => (
              <span
                key={item.title}
                className={cn("h-1.5 rounded-full bg-muted-foreground/30 transition-all", n === slide ? "w-6 bg-primary" : "w-1.5")}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {!last && (
              <Button variant="ghost" onClick={onClose}>
                Skip
              </Button>
            )}
            <Button onClick={() => (last ? onClose() : setSlide(slide + 1))}>
              {last ? "Start reviewing" : "Next"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

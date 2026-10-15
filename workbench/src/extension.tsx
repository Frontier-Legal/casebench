// What a team build adds to the workbench (decision 0058). The core build has nothing here; the
// build of casebench-ee points "@/extension" at its own module, which fills these in.

import type { ComponentType, ReactNode } from "react"

import type { Me } from "@/lib/api"

export interface ExtraPage {
  id: string
  title: string
  icon: ComponentType
  /** The permission the page needs, such as admin. */
  needs: string
  render: (me: Me) => ReactNode
}

export interface Extension {
  /** Pages added to the sidebar, below the core's. */
  pages: ExtraPage[]
  /** Stands in front of the app until someone is signed in; the core asks for a name. */
  Gate?: ComponentType<{ children: ReactNode }>
}

export const extension: Extension = { pages: [] }

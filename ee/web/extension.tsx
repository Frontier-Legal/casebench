// SPDX-License-Identifier: Elastic-2.0
// What the team build adds to the workbench: sign-in in front of it, and the Team and Audit log
// pages (decision 0058). The build points "@/extension" here.

import { ScrollTextIcon, UsersIcon } from "lucide-react"

import type { Extension } from "../../workbench/src/extension"

import { team } from "./api"
import { AuditLog } from "./audit-log"
import { TeamGate } from "./gate"
import { TeamAdmin } from "./team-admin"

export const extension: Extension = {
  Gate: TeamGate,
  pages: [
    { id: "audit", title: "Audit log", icon: ScrollTextIcon, needs: "edit", render: () => <AuditLog /> },
    { id: "team", title: "Team", icon: UsersIcon, needs: "admin", render: () => <TeamAdmin /> },
  ],
  signOut: async () => {
    await team.signOut()
  },
}

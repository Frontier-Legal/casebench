// The setup as the server would show it, for the page tests: a settings view built from the
// sections a test names, and the people who open the workbench.

import type { KeyView, Me, ModelView, Sections, SettingsView } from "@/lib/api"

export const ENGINEER: Me = { name: "Deniz Kaya", view: "engineering", role_locked: false, role: "engineer", setup: true }

export const JUDGE: ModelView = {
  role: "judge",
  used_for: "Lists each answer's citations",
  provider: "anthropic",
  model: "claude-judge",
  family: "claude",
  max_tokens: 4096,
  context_window: 200000,
  price_input: 3,
  price_output: 15,
  settings: {},
  key: "ANTHROPIC_API_KEY",
  base_url: null,
}

export function settingsView(sections: Sections, models: ModelView[] = [], keys: KeyView[] = []): SettingsView {
  return {
    file: "casebench.yaml",
    exists: Object.keys(sections).length > 0,
    editable: true,
    problem: null,
    has_comments: false,
    sections,
    text: "",
    models,
    keys,
    budget: null,
    runs: [],
    plugins: { targets: ["python", "http", "command"], connectors: ["folder", "http", "mcp"], providers: ["anthropic", "openai"] },
  }
}

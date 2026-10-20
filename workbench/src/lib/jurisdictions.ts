// A jurisdiction code as a person reads it: its name from the browser's own list and its flag
// from the code's letters (decision 0065).

const EU = "EU"
// Unicode's regional indicator symbols start here; a two-letter region code maps onto them.
const REGIONAL_A = 0x1f1e6

let names: Intl.DisplayNames | null | undefined

function regionNames(): Intl.DisplayNames | null {
  if (names === undefined) {
    try {
      names = new Intl.DisplayNames(["en"], { type: "region", fallback: "none" })
    } catch {
      names = null
    }
  }
  return names
}

/** France for FR, California (US) for US-CA, the code itself when nothing names it. */
export function jurisdictionName(code: string): string {
  if (code === EU) return "European Union"
  const [country, part] = code.split("-")
  const name = regionNames()?.of(country) ?? country
  return part ? `${name}, ${part}` : name
}

/** The flag a browser draws for a country; the letters themselves where it draws none. */
export function flag(code: string): string {
  const country = code.split("-")[0]
  if (!/^[A-Z]{2}$/.test(country)) return ""
  return String.fromCodePoint(...[...country].map((letter) => REGIONAL_A + letter.charCodeAt(0) - 65))
}

/** Codes sorted by the names people know them by. */
export function byName(codes: string[]): string[] {
  return [...codes].sort((a, b) => jurisdictionName(a).localeCompare(jurisdictionName(b)))
}

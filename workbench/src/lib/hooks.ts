import { useEffect, useRef, useState } from "react"

/** Whether the screen is wide enough for two columns. */
export function useWide(query = "(min-width: 1024px)"): boolean {
  const [wide, setWide] = useState(() =>
    typeof window !== "undefined" && window.matchMedia
      ? window.matchMedia(query).matches
      : true,
  )
  useEffect(() => {
    if (!window.matchMedia) return
    const media = window.matchMedia(query)
    const change = () => setWide(media.matches)
    media.addEventListener?.("change", change)
    return () => media.removeEventListener?.("change", change)
  }, [query])
  return wide
}

/** Calls `save` with the latest value once it has stopped changing for `wait` ms. */
export function useAutosave<T>(value: T, save: (value: T) => void, wait = 400): void {
  const first = useRef(true)
  const latest = useRef(save)
  latest.current = save
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    const timer = window.setTimeout(() => latest.current(value), wait)
    return () => window.clearTimeout(timer)
  }, [value, wait])
}

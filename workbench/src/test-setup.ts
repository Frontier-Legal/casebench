import "@testing-library/jest-dom/vitest"

// jsdom has no layout: a wide screen, no motion, and no scrolling.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: query.includes("min-width"),
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
})
window.scrollTo = () => {}
Element.prototype.scrollIntoView = () => {}
Element.prototype.scrollTo = () => {}
class NoResize {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = window.ResizeObserver ?? (NoResize as unknown as typeof ResizeObserver)
if (!("escape" in CSS)) {
  Object.assign(CSS, { escape: (value: string) => value.replace(/["\\]/g, "\\$&") })
}

// Radix's select reads pointer capture, which jsdom does not have.
Element.prototype.hasPointerCapture = Element.prototype.hasPointerCapture ?? (() => false)
Element.prototype.releasePointerCapture = Element.prototype.releasePointerCapture ?? (() => {})

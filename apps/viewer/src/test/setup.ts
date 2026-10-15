import '@testing-library/jest-dom/vitest'
import { MotionGlobalConfig } from 'motion/react'

// Animations finish instantly so exit transitions never hold the previous view.
MotionGlobalConfig.skipAnimations = true

// Plugin tests run in Node, without a DOM.
if (typeof window !== 'undefined') {
  // jsdom lacks the layout and media APIs the canvas and Radix use.
  window.matchMedia ??= (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList

  globalThis.ResizeObserver ??= class {
    constructor(private cb: ResizeObserverCallback) {}
    observe(el: Element) {
      this.cb([{ target: el } as ResizeObserverEntry], this as unknown as ResizeObserver)
    }
    unobserve() {}
    disconnect() {}
  }

  Element.prototype.scrollIntoView ??= () => {}
  Element.prototype.scrollTo ??= () => {}
  Element.prototype.hasPointerCapture ??= () => false
  Element.prototype.releasePointerCapture ??= () => {}
}

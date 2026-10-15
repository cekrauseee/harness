import type { Transition, Variants } from 'motion/react'

// Motion language shared by the whole app: one easing, one "rise" entrance, cascades by nesting.
export const EASE = [0.2, 0.8, 0.2, 1] as const
export const SPRING: Transition = { type: 'spring', stiffness: 420, damping: 42 }

/** An element rises in when its nearest animated ancestor goes to "show"; nested ones cascade after it. */
export const rise: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: EASE, staggerChildren: 0.03 } },
}

export const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

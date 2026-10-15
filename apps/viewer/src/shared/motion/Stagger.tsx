import type { ElementType } from 'react'
import { motion, type HTMLMotionProps } from 'motion/react'
import { rise } from './tokens'

type Tag = 'div' | 'li' | 'ol' | 'p' | 'span' | 'button' | 'section' | 'header'
type Props<T extends Tag> = HTMLMotionProps<T> & { as?: T }

/** Starts a cascade: its Items (and their nested Items) rise in one after another. */
export function Stagger<T extends Tag = 'div'>({ as, gap = 0.035, delay = 0, ...rest }: Props<T> & { gap?: number; delay?: number }) {
  const C = motion[as ?? 'div'] as ElementType
  return (
    <C
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap, delayChildren: delay } } }}
      {...rest}
    />
  )
}

/** One step of a cascade. */
export function Item<T extends Tag = 'div'>({ as, style, ...rest }: Props<T>) {
  const C = motion[as ?? 'div'] as ElementType
  return <C variants={rise} style={{ willChange: 'transform, opacity', ...style }} {...rest} />
}

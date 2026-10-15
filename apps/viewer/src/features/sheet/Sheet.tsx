import type { ReactNode } from 'react'
import { AnimatePresence, motion, type Variants } from 'motion/react'
import { ArrowLeft } from 'lucide-react'
import { EASE, SPRING } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { ScrollArea } from '@/shared/ui/scroll-area'

// A view slides in the direction of navigation, then its sections cascade in.
const viewMotion: Variants = {
  hidden: (dir: number) => ({ opacity: 0, x: dir * 20 }),
  show: { opacity: 1, x: 0, transition: { duration: 0.32, ease: EASE, staggerChildren: 0.045, delayChildren: 0.03 } },
  exit: (dir: number) => ({ opacity: 0, x: dir * -20, transition: { duration: 0.14, ease: 'easeIn' } }),
}
const headSwap: Variants = {
  hidden: (dir: number) => ({ opacity: 0, x: dir * 10 }),
  show: { opacity: 1, x: 0, transition: { duration: 0.26, ease: EASE } },
  exit: (dir: number) => ({ opacity: 0, x: dir * -10, transition: { duration: 0.12 } }),
}

interface Props {
  open: boolean
  title: string
  subtitle?: string
  /** Identifies the current view; changing it plays the navigation transition. */
  viewKey: string
  /** Present on detail views: the header shows Back instead of the title. */
  onBack?: () => void
  children: ReactNode
}

/** Floating panel on the left (bottom on small screens) holding the index and every detail view. */
export function Sheet({ open, title, subtitle, viewKey, onBack, children }: Props) {
  const dir = onBack ? 1 : -1
  return (
    <motion.aside
      aria-label="Details"
      initial={{ x: -24, opacity: 0 }}
      animate={open ? { x: 0, opacity: 1 } : { x: -420, opacity: 0 }}
      transition={SPRING}
      aria-hidden={!open}
      inert={!open}
      className={cn(
        'cm-float absolute top-3 bottom-3 left-3 z-20 flex w-[392px] flex-col overflow-hidden rounded-[14px] border',
        'max-md:top-auto max-md:right-2 max-md:bottom-2 max-md:left-2 max-md:h-[52vh] max-md:w-auto',
        !open && 'pointer-events-none',
      )}
    >
      {/* Fixed-height header: title and Back swap in place, so the panel never jumps. */}
      <div className="relative h-[66px] shrink-0 overflow-hidden border-b">
        <AnimatePresence initial={false} custom={dir}>
          <motion.div
            key={onBack ? 'back' : 'title'}
            custom={dir}
            variants={headSwap}
            initial="hidden"
            animate="show"
            exit="exit"
            className="absolute inset-x-5 top-1/2 -translate-y-1/2"
          >
            {onBack ? (
              <Button variant="ghost" size="sm" className="-ml-2 h-8 gap-1.5 px-2 text-[12.5px] text-muted-foreground" onClick={onBack}>
                <ArrowLeft />
                Back
              </Button>
            ) : (
              <>
                <h1 className="truncate text-[14.5px] leading-tight font-semibold tracking-[-0.01em]">{title}</h1>
                {subtitle && <p className="mt-1 truncate font-mono text-[11.5px] leading-tight text-muted-foreground">{subtitle}</p>}
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.div
            key={viewKey}
            custom={dir}
            variants={viewMotion}
            initial="hidden"
            animate="show"
            exit="exit"
            style={{ willChange: 'transform, opacity' }}
            className="flex min-w-0 flex-col gap-[22px] p-5"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </ScrollArea>
    </motion.aside>
  )
}

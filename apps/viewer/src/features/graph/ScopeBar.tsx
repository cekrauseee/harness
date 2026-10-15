import { motion } from 'motion/react'
import { ArrowLeft, ChevronRight } from 'lucide-react'
import { SPRING } from '@/shared/motion'
import { Button } from '@/shared/ui/button'

/** Shown while the canvas is drilled into one module of a large change. */
export function ScopeBar({ title, left, onExit }: { title: string; left: number; onExit: () => void }) {
  return (
    <motion.nav
      aria-label="Module"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={SPRING}
      style={{ left }}
      className="cm-float absolute top-3 z-10 flex min-w-0 items-center gap-0.5 rounded-xl border p-1 transition-[left] duration-500 ease-out-soft"
    >
      <Button variant="ghost" size="sm" onClick={onExit} className="gap-1.5 text-[12.5px] text-muted-foreground">
        <ArrowLeft />
        All modules
      </Button>
      <ChevronRight className="size-3.5 shrink-0 text-muted-foreground/60" />
      <span aria-current="location" className="truncate px-2 text-[12.5px] font-medium">
        {title}
      </span>
    </motion.nav>
  )
}

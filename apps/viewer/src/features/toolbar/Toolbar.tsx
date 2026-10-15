import type { ReactNode, RefObject } from 'react'
import { motion } from 'motion/react'
import { LayoutGrid, Maximize, Minus, Monitor, Moon, PanelLeft, Plus, Search, Sun } from 'lucide-react'
import { Item } from '@/shared/motion'
import { Button } from '@/shared/ui/button'
import { Kbd } from '@/shared/ui/kbd'
import { Separator } from '@/shared/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/shared/ui/tooltip'

export type Theme = 'system' | 'light' | 'dark'
const THEME: Record<Theme, [typeof Monitor, Theme]> = { system: [Monitor, 'light'], light: [Sun, 'dark'], dark: [Moon, 'system'] }

/** What the toolbar drives on the canvas. */
export interface CanvasControls {
  fit: () => void
  zoomIn: () => void
  zoomOut: () => void
  resetZoom: () => void
  relayout: () => void
}

function Tool({
  label,
  kbd,
  onClick,
  children,
  active,
}: {
  label: string
  kbd?: string
  onClick: () => void
  children: ReactNode
  active?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Item as="span" className="inline-flex">
          <Button
            variant="ghost"
            size="icon"
            onClick={onClick}
            aria-label={label}
            aria-pressed={active}
            className="rounded-lg text-muted-foreground hover:text-foreground"
          >
            {children}
          </Button>
        </Item>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={8}>
        {label}
        {kbd && <Kbd className="ml-1.5">{kbd}</Kbd>}
      </TooltipContent>
    </Tooltip>
  )
}

interface Props {
  canvas: RefObject<CanvasControls | null>
  zoom: number
  sheetOpen: boolean
  onToggleSheet: () => void
  onSearch: () => void
  theme: Theme
  onTheme: (theme: Theme) => void
  right: number
}

export function Toolbar({ canvas, zoom, sheetOpen, onToggleSheet, onSearch, theme, onTheme, right }: Props) {
  const [ThemeIcon, next] = THEME[theme]
  return (
    <motion.div
      role="toolbar"
      aria-label="Canvas tools"
      initial="hidden"
      animate="show"
      style={{ right }}
      variants={{
        hidden: { opacity: 0, y: 12 },
        show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 380, damping: 36, delayChildren: 0.25, staggerChildren: 0.03 } },
      }}
      className="cm-float absolute bottom-3 z-30 flex items-center gap-0.5 rounded-xl border p-1 transition-[right] duration-500 ease-out-soft max-md:hidden"
    >
      <Tool label={sheetOpen ? 'Hide panel' : 'Show panel'} onClick={onToggleSheet} active={sheetOpen}>
        <PanelLeft />
      </Tool>
      <Tool label="Search" kbd="⌘K" onClick={onSearch}>
        <Search />
      </Tool>
      <Separator orientation="vertical" className="mx-1 h-5" />
      <Tool label="Zoom out" onClick={() => canvas.current?.zoomOut()}>
        <Minus />
      </Tool>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            className="w-14 font-mono text-[11px] text-muted-foreground tabular-nums"
            onClick={() => canvas.current?.resetZoom()}
          >
            {Math.round(zoom * 100)}%
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={8}>
          Reset to 100%
        </TooltipContent>
      </Tooltip>
      <Tool label="Zoom in" onClick={() => canvas.current?.zoomIn()}>
        <Plus />
      </Tool>
      <Separator orientation="vertical" className="mx-1 h-5" />
      <Tool label="Fit to screen" onClick={() => canvas.current?.fit()}>
        <Maximize />
      </Tool>
      <Tool label="Reorganize cards" onClick={() => canvas.current?.relayout()}>
        <LayoutGrid />
      </Tool>
      <Separator orientation="vertical" className="mx-1 h-5" />
      <Tool label={`Theme: ${theme}`} onClick={() => onTheme(next)}>
        <ThemeIcon />
      </Tool>
    </motion.div>
  )
}

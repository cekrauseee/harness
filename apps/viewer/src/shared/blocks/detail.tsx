import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { ChevronDown, Code2 } from 'lucide-react'
import { useMap, type MapFile } from '@/data'
import { Item, rise } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/shared/ui/collapsible'
import { LayerDot } from './LayerDot'
import { FILE_STATUS, TONE, type Tone } from './tones'

// Building blocks of every detail view: the same header, eyebrow-titled sections, references and chips.

export function Section({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <motion.section variants={rise} style={{ willChange: 'transform, opacity' }} className={cn('flex min-w-0 flex-col gap-2.5', className)}>
      <h4 className="cm-eyebrow">{title}</h4>
      {children}
    </motion.section>
  )
}

export function Header({
  tag,
  layer,
  title,
  sub,
  children,
}: {
  tag: string
  layer?: number
  title: string
  sub?: string
  children?: ReactNode
}) {
  return (
    <motion.header variants={rise} style={{ willChange: 'transform, opacity' }} className="flex min-w-0 flex-col">
      <span className="cm-eyebrow flex items-center gap-1.5">
        {layer !== undefined && <LayerDot layer={layer} />}
        {tag}
      </span>
      <h2 className="mt-1.5 text-[19px] leading-tight font-semibold tracking-tight [overflow-wrap:anywhere]">{title}</h2>
      {sub && <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{sub}</p>}
      {children}
    </motion.header>
  )
}

export function Prose({ children, muted }: { children: ReactNode; muted?: boolean }) {
  return <p className={cn('text-[13px] leading-relaxed [overflow-wrap:anywhere]', muted && 'text-muted-foreground')}>{children}</p>
}

export function Tag({ tone = 'neutral', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <Badge variant="secondary" className={cn('rounded-md font-mono text-[10px] tracking-wide uppercase', TONE[tone], className)}>
      {children}
    </Badge>
  )
}

/** Card references as chips; unknown ids (a map still being written) are skipped. */
export function CardChips({ ids, onSelect }: { ids: string[]; onSelect: (id: string) => void }) {
  const { cards, layerSlot } = useMap()
  return (
    <div className="flex flex-wrap gap-1.5">
      {ids.flatMap((id) => {
        const card = cards.get(id)
        return card
          ? [
              <Button key={id} variant="outline" size="sm" className="h-7 rounded-full px-2.5 font-normal" onClick={() => onSelect(id)}>
                <LayerDot layer={layerSlot(card.layer)} />
                {card.title}
              </Button>,
            ]
          : []
      })}
    </div>
  )
}

/** Reference to code: mono "where" line over a sentence; opens the code panel. */
export function CodeRef({ meta, text, onOpen }: { meta: string; text?: string; onOpen: () => void }) {
  return (
    <motion.button
      variants={rise}
      onClick={onOpen}
      className="group flex w-full min-w-0 flex-col gap-1 rounded-lg border border-transparent bg-secondary/70 px-3 py-2.5 text-left transition-colors hover:border-border hover:bg-background"
    >
      <span className="flex min-w-0 items-center gap-1.5 font-mono text-[11px] leading-snug [overflow-wrap:anywhere] text-muted-foreground">
        <Code2 className="size-3 shrink-0 transition-colors group-hover:text-brand" />
        {meta}
      </span>
      {text && <span className="text-[12.5px] leading-normal [overflow-wrap:anywhere]">{text}</span>}
    </motion.button>
  )
}

export function Refs({ children }: { children: ReactNode }) {
  return <div className="grid gap-1.5">{children}</div>
}

export function StatusBadge({ file }: { file?: MapFile }) {
  if (!file) return null
  const [label, tone] = FILE_STATUS[file.status]
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 font-mono text-[10.5px]">
      <Tag tone={tone}>{label}</Tag>
      {file.status !== 'deleted' && <span className="text-ok">+{file.added ?? '–'}</span>}
      {file.status !== 'added' && <span className="text-destructive">−{file.deleted ?? '–'}</span>}
    </span>
  )
}

export function Steps({ items }: { items: ReactNode[] }) {
  return (
    <ol className="grid gap-2.5">
      {items.map((s, i) => (
        <Item as="li" key={i} className="grid grid-cols-[22px_minmax(0,1fr)] gap-2.5 text-[13px] leading-relaxed">
          <span className="grid size-[22px] place-items-center rounded-full bg-secondary font-mono text-[11px] text-muted-foreground">
            {i + 1}
          </span>
          <span className="pt-px">{s}</span>
        </Item>
      ))}
    </ol>
  )
}

export function Disclosure({
  label,
  open,
  onOpenChange,
  children,
  className,
}: {
  label: string
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
  className?: string
}) {
  return (
    <Collapsible open={open} onOpenChange={onOpenChange} className={cn('min-w-0', className)}>
      <CollapsibleTrigger asChild>
        <button className="group inline-flex items-center gap-1.5 py-1 text-[12.5px] text-muted-foreground transition-colors hover:text-foreground">
          <ChevronDown className="size-3.5 -rotate-90 transition-transform duration-200 group-data-[state=open]:rotate-0" />
          {label}
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

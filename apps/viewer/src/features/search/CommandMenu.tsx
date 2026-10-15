import type { ReactNode } from 'react'
import { Footprints, Route } from 'lucide-react'
import { useMap, type Selection } from '@/data'
import { LayerDot, SEVERITY_DOT, STATUS_TEXT } from '@/shared/blocks'
import { cn } from '@/shared/lib/utils'
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/shared/ui/command'
import { Kbd } from '@/shared/ui/kbd'

const group =
  '[&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:text-[10.5px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:tracking-[0.08em] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted-foreground'

interface RowProps {
  value: string
  onSelect: () => void
  lead: ReactNode
  title: ReactNode
  sub?: string
  meta?: string
  metaClass?: string
}

// Leading mark, title (with an optional muted second part) and right-aligned meta.
function Row({ value, onSelect, lead, title, sub, meta, metaClass }: RowProps) {
  return (
    <CommandItem value={value} onSelect={onSelect} className="gap-2.5 rounded-lg px-2.5 py-2 data-[selected=true]:bg-secondary">
      <span className="grid size-4 shrink-0 place-items-center text-muted-foreground">{lead}</span>
      <span className="flex min-w-0 flex-1 items-baseline gap-2">
        <span className="truncate text-[13px]">{title}</span>
        {sub && <span className="truncate font-mono text-[11px] text-muted-foreground">{sub}</span>}
      </span>
      {meta && <span className={cn('shrink-0 font-mono text-[10.5px] text-muted-foreground', metaClass)}>{meta}</span>}
    </CommandItem>
  )
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectCard: (id: string) => void
  onSelect: (selection: Selection) => void
  onOpenFile: (path: string) => void
}

/** ⌘K: jump to any card, flow, attention point or file. */
export function CommandMenu({ open, onOpenChange, onSelectCard, onSelect, onOpenFile }: Props) {
  const { map, layerSlot, layerTitle } = useMap()
  const run = (fn: () => void) => () => {
    onOpenChange(false)
    fn()
  }
  const files = Object.entries(map.files).sort(([a], [b]) => a.localeCompare(b))
  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search the change"
      description="Cards, flows, attention points and files"
      className="cm-float top-[18vh] max-w-[620px]! rounded-[14px]! border sm:max-w-[620px]!"
    >
      <Command className="bg-transparent">
        <CommandInput placeholder="Search cards, flows, files…" className="h-11 text-[13.5px]" />
        <CommandList className="max-h-[min(440px,56vh)] px-1.5 pb-1.5">
          <CommandEmpty className="py-10 text-center text-[13px] text-muted-foreground">Nothing matches.</CommandEmpty>
          <CommandGroup heading="Cards" className={group}>
            {map.cards.map((c) => (
              <Row
                key={c.id}
                value={`card ${c.id} ${c.title} ${c.summary} ${layerTitle(c.layer)}`}
                onSelect={run(() => onSelectCard(c.id))}
                lead={<LayerDot layer={layerSlot(c.layer)} className="size-2" />}
                title={c.title}
                meta={layerTitle(c.layer)}
              />
            ))}
          </CommandGroup>
          {map.flows.length > 0 && (
            <CommandGroup heading="Flows" className={group}>
              {map.flows.map((f) => (
                <Row
                  key={f.id}
                  value={`flow ${f.id} ${f.title} ${f.trigger ?? ''} ${f.outcome ?? ''}`}
                  onSelect={run(() => onSelect({ kind: 'flow', id: f.id, step: 0 }))}
                  lead={f.steps.length ? <Footprints className="size-3.5" /> : <Route className="size-3.5" />}
                  title={f.title}
                  meta={f.steps.length ? `${f.steps.length} steps` : `${f.cards.length} cards`}
                />
              ))}
            </CommandGroup>
          )}
          {map.attention.length > 0 && (
            <CommandGroup heading="Attention" className={group}>
              {map.attention.map((a) => (
                <Row
                  key={a.id}
                  value={`attention ${a.id} ${a.title} ${a.category ?? ''} ${a.severity ?? ''}`}
                  onSelect={run(() => onSelect({ kind: 'attention', id: a.id }))}
                  lead={<i className={cn('size-1.5 rounded-full', a.severity ? SEVERITY_DOT[a.severity] : 'bg-muted-foreground/20')} />}
                  title={a.title}
                  meta={a.status}
                  metaClass={STATUS_TEXT[a.status]}
                />
              ))}
            </CommandGroup>
          )}
          {files.length > 0 && (
            <CommandGroup heading="Files" className={group}>
              {files.map(([p, f]) => {
                const i = p.lastIndexOf('/')
                const isNew = f.status === 'added'
                return (
                  <Row
                    key={p}
                    value={`file ${p}`}
                    onSelect={run(() => onOpenFile(p))}
                    lead={<i className={cn('size-1.5 rounded-full', isNew ? 'bg-ok' : 'bg-muted-foreground/40')} />}
                    title={<span className="font-mono text-[12.5px]">{p.slice(i + 1)}</span>}
                    sub={p.slice(0, i + 1)}
                    meta={isNew ? 'new' : f.status}
                    metaClass={isNew ? 'text-ok' : undefined}
                  />
                )
              })}
            </CommandGroup>
          )}
        </CommandList>
        <div className="flex items-center gap-4 border-t px-3.5 py-2 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Kbd>↑</Kbd>
            <Kbd>↓</Kbd>navigate
          </span>
          <span className="flex items-center gap-1.5">
            <Kbd>↵</Kbd>open
          </span>
          <span className="flex items-center gap-1.5">
            <Kbd>esc</Kbd>close
          </span>
        </div>
      </Command>
    </CommandDialog>
  )
}

import { motion } from 'motion/react'
import { useMap, type MapAttention, type Selection } from '@/data'
import { SEVERITY_DOT, STATUS_TEXT } from '@/shared/blocks'
import { Item, rise } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { Tabs, TabsList, TabsTrigger } from '@/shared/ui/tabs'
import { Overview } from './Overview'

export type IndexTab = 'flows' | 'attention'
const LABELS: Record<IndexTab, string> = { flows: 'Flows', attention: 'Attention' }
const COLS = ['', 'grid-cols-1', 'grid-cols-2']

interface Entry {
  key: string
  title: string
  aside: string
  selection: Selection
  severity?: MapAttention['severity']
  status?: MapAttention['status']
}

/** Home view: a segmented control over flows and attention points, then the overview. */
export function IndexView({ tab, onTab, onSelect }: { tab: IndexTab; onTab: (tab: IndexTab) => void; onSelect: (s: Selection) => void }) {
  const { map } = useMap()
  const lists: Record<IndexTab, Entry[]> = {
    flows: map.flows.map((f) => ({
      key: f.id,
      title: f.title,
      aside: f.steps.length ? `${f.steps.length} steps` : `${f.cards.length} cards`,
      selection: { kind: 'flow', id: f.id, step: 0 },
    })),
    attention: map.attention.map((a) => ({
      key: a.id,
      title: a.title,
      aside: a.status,
      severity: a.severity,
      status: a.status,
      selection: { kind: 'attention', id: a.id },
    })),
  }
  const tabs = (Object.keys(LABELS) as IndexTab[]).filter((k) => lists[k].length)
  const current = tabs.includes(tab) ? tab : tabs[0]

  return (
    <>
      {current && (
        <>
          <motion.div variants={rise}>
            <Tabs value={current} onValueChange={(v) => onTab(v as IndexTab)}>
              <TabsList className={cn('grid h-9 w-full gap-0 rounded-[10px] border bg-secondary p-[3px]', COLS[tabs.length])}>
                {tabs.map((k) => (
                  <TabsTrigger
                    key={k}
                    value={k}
                    className="relative h-full rounded-[7px] border-0 px-2 py-0 text-[12.5px] text-muted-foreground! shadow-none! transition-colors hover:text-foreground/80! data-active:bg-transparent! data-active:text-foreground! dark:data-active:border-transparent! dark:data-active:bg-transparent!"
                  >
                    {current === k && (
                      <motion.span
                        layoutId="tab-pill"
                        transition={{ type: 'spring', stiffness: 500, damping: 46 }}
                        className="absolute inset-0 rounded-[7px] bg-background shadow-[0_1px_2px_rgba(0,0,0,.08),0_0_0_1px_var(--border)]"
                      />
                    )}
                    <span className="relative z-10 font-medium">{LABELS[k]}</span>
                    <span className="relative z-10 font-mono text-[10px] text-muted-foreground">{lists[k].length}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </motion.div>
          {/* keyed by tab so switching tabs replays the cascade */}
          <motion.div
            key={current}
            initial="hidden"
            animate="show"
            variants={{ hidden: {}, show: { transition: { staggerChildren: 0.022 } } }}
            className="-mx-2 -mt-3 grid gap-px"
          >
            {lists[current].map((it) => (
              <Item
                as="button"
                key={it.key}
                onClick={() => onSelect(it.selection)}
                className="flex min-w-0 items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors hover:bg-secondary"
              >
                {it.status && (
                  <i className={cn('size-1.5 shrink-0 rounded-full', it.severity ? SEVERITY_DOT[it.severity] : 'bg-muted-foreground/20')} />
                )}
                <span className="min-w-0 flex-1 truncate">{it.title}</span>
                <span className={cn('shrink-0 font-mono text-[10.5px] text-muted-foreground', it.status && STATUS_TEXT[it.status])}>
                  {it.aside}
                </span>
              </Item>
            ))}
          </motion.div>
        </>
      )}
      <Overview />
    </>
  )
}

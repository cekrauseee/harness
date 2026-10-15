import { motion } from 'motion/react'
import { changeStats, useMap, type MapRun } from '@/data'
import { LayerDot, Prose, Section } from '@/shared/blocks'
import { Item, rise } from '@/shared/motion'

const compact = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${Math.round(n / 1e3)}k` : String(n))
const tokens = (r: MapRun) => {
  const t = r.tokens
  if (!t) return ''
  if (t.input !== undefined) return `${compact(t.input)} in${t.output !== undefined ? ` · ${compact(t.output)} out` : ''}`
  return t.total !== undefined ? `${compact(t.total)} tokens` : ''
}

/** The change at a glance: summary, counts, follow-ups, the runs it was built from and the layer legend. */
export function Overview() {
  const { map } = useMap()
  const s = changeStats(map)
  const stats: [number, string][] = [
    [s.files, 'files changed'],
    [s.added, 'new files'],
    [s.changed, 'with new code'],
    [s.critical, 'critical points'],
  ]
  return (
    <>
      {map.subtitle && (
        <motion.div variants={rise}>
          <Prose muted>{map.subtitle}</Prose>
        </motion.div>
      )}
      {s.files > 0 && (
        <motion.div variants={rise} className="grid grid-cols-4 [gap:1px] overflow-hidden rounded-xl border bg-border">
          {stats.map(([n, label]) => (
            <div key={label} className="flex flex-col gap-0.5 bg-card px-2.5 py-2.5">
              <b className="text-[17px] font-semibold tracking-tight tabular-nums">{n}</b>
              <span className="text-[10.5px] leading-tight text-muted-foreground">{label}</span>
            </div>
          ))}
        </motion.div>
      )}
      {map.followups.length > 0 && (
        <Section title={`Follow-ups · ${map.followups.length}`}>
          <ul className="grid gap-2">
            {map.followups.map((f, i) => (
              <Item as="li" key={i} className="flex min-w-0 flex-col gap-0.5 text-[13px] leading-relaxed">
                {f.text}
                {(f.front || f.run) && (
                  <span className="font-mono text-[10.5px] text-muted-foreground">{[f.front, f.run].filter(Boolean).join(' · ')}</span>
                )}
              </Item>
            ))}
          </ul>
        </Section>
      )}
      {map.runs.length > 0 && (
        <Section title={`Built from · ${map.runs.length} ${map.runs.length === 1 ? 'run' : 'runs'}`}>
          <ul className="grid gap-2">
            {map.runs.map((r) => {
              const meta = [r.kind, r.host, r.model, tokens(r)].filter(Boolean).join(' · ')
              return (
                <Item as="li" key={`${r.front}/${r.run}`} className="flex min-w-0 flex-col font-mono text-[11px] leading-snug">
                  <span className="truncate">
                    {r.front} · {r.run}
                  </span>
                  <span className="truncate text-muted-foreground">{meta}</span>
                </Item>
              )
            })}
          </ul>
        </Section>
      )}
      <Section title="Legend">
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[12.5px] text-muted-foreground">
          {map.layers.map((l, i) => (
            <span key={l.id} className="flex min-w-0 items-center gap-2">
              <LayerDot layer={i} />
              <span className="truncate">{l.title}</span>
            </span>
          ))}
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          Arrows point from caller to dependency. Drag to pan, ⌘/Ctrl + scroll to zoom, ⌘K to search.
        </p>
      </Section>
    </>
  )
}

import { useState } from 'react'
import { edgeLabels, hunkNote, linesLabel, notesFor, refTarget, testMeta, testsFor, useMap, type MapCard, type Selection } from '@/data'
import { CardChips, CodeRef, Disclosure, Header, Prose, Refs, Section, SEVERITY_DOT, STATUS_TEXT, StatusBadge } from '@/shared/blocks'
import { Item } from '@/shared/motion'
import { count } from '@/shared/lib/plural'
import { cn } from '@/shared/lib/utils'

interface Actions {
  onSelectCard: (id: string) => void
  onSelect: (selection: Selection) => void
  onOpenCode: (path: string, target?: string | null) => void
}

function FileRow({ path, onOpenCode }: { path: string } & Pick<Actions, 'onOpenCode'>) {
  const [open, setOpen] = useState(false)
  const { map } = useMap()
  const file = map.files[path]
  const code = map.code[path]
  const i = path.lastIndexOf('/')
  const changes = code?.hunks
    ? code.hunks.map((h, j) => ({ id: `hunk-${j}`, label: `Change ${j + 1}${h.context ? ` · ${h.context}` : ''}`, note: hunkNote(map, h) }))
    : notesFor(map, path).map((n) => ({ id: refTarget(n)!, label: `${linesLabel(n.start, n.end)} · ${n.symbol}`, note: n.text }))
  return (
    <Item as="li" className={cn('flex min-w-0 flex-col gap-0.5 border-l-2 pl-3', file?.status === 'added' ? 'border-ok' : 'border-border')}>
      <button
        className="group flex min-w-0 items-center gap-2 text-left disabled:cursor-default"
        onClick={() => onOpenCode(path)}
        disabled={!file}
        title={path}
      >
        <span className="truncate font-mono text-[12.5px] font-medium transition-colors group-hover:text-brand">{path.slice(i + 1)}</span>
        <StatusBadge file={file} />
      </button>
      {i > 0 && (
        <span className="font-mono text-[11px] text-muted-foreground/80">
          {path
            .slice(0, i + 1)
            .split('/')
            .map((p, k, a) => (
              <span key={k}>
                {p}
                {k < a.length - 1 && (
                  <>
                    /<wbr />
                  </>
                )}
              </span>
            ))}
        </span>
      )}
      {file?.role && <p className="mt-1 text-[12.5px] leading-normal text-muted-foreground">{file.role}</p>}
      {changes.length > 0 && (
        <Disclosure label={`${open ? 'Hide' : 'Show'} ${count(changes.length, 'change')}`} open={open} onOpenChange={setOpen}>
          <Refs>
            {changes.map((c) => (
              <CodeRef key={c.id} meta={c.label} text={c.note} onOpen={() => onOpenCode(path, c.id)} />
            ))}
          </Refs>
        </Disclosure>
      )}
    </Item>
  )
}

/** A row that opens another detail: leading mark, title and mono meta. */
function LinkRow({
  mark,
  title,
  meta,
  metaClass,
  onClick,
}: {
  mark?: string
  title: string
  meta: string
  metaClass?: string
  onClick: () => void
}) {
  return (
    <Item
      as="button"
      onClick={onClick}
      className="-mx-2 flex min-w-0 items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-[13px] transition-colors hover:bg-secondary"
    >
      {mark && <i className={cn('size-1.5 shrink-0 rounded-full', mark)} />}
      <span className="min-w-0 flex-1 truncate">{title}</span>
      <span className={cn('shrink-0 font-mono text-[10.5px] text-muted-foreground', metaClass)}>{meta}</span>
    </Item>
  )
}

export function CardDetail({ card, onSelectCard, onSelect, onOpenCode }: { card: MapCard } & Actions) {
  const { map, out, in: callers, layerSlot, layerTitle } = useMap()
  const deps = out.get(card.id) ?? []
  const usedBy = callers.get(card.id) ?? []
  const points = map.attention.filter((a) => card.attention.includes(a.id) || a.cards.includes(card.id))
  const flows = map.flows.filter((f) => card.flows.includes(f.id) || f.cards.includes(card.id))
  const tests = testsFor(map, card)
  return (
    <>
      <Header tag={layerTitle(card.layer)} layer={layerSlot(card.layer)} title={card.title} />
      <Section title="What it does">
        <Prose>{card.summary}</Prose>
      </Section>
      {deps.length > 0 && (
        <Section title="Depends on">
          <CardChips ids={deps} onSelect={onSelectCard} labels={edgeLabels(map, card.id, 'out')} />
        </Section>
      )}
      {usedBy.length > 0 && (
        <Section title="Used by">
          <CardChips ids={usedBy} onSelect={onSelectCard} labels={edgeLabels(map, card.id, 'in')} />
        </Section>
      )}
      {points.length > 0 && (
        <Section title="Attention">
          <div className="grid gap-px">
            {points.map((a) => (
              <LinkRow
                key={a.id}
                mark={a.severity && SEVERITY_DOT[a.severity]}
                title={a.title}
                meta={a.status}
                metaClass={STATUS_TEXT[a.status]}
                onClick={() => onSelect({ kind: 'attention', id: a.id })}
              />
            ))}
          </div>
        </Section>
      )}
      {flows.length > 0 && (
        <Section title="Flows">
          <div className="grid gap-px">
            {flows.map((f) => (
              <LinkRow
                key={f.id}
                title={f.title}
                meta={count(f.steps.length, 'step')}
                onClick={() => onSelect({ kind: 'flow', id: f.id, step: 0 })}
              />
            ))}
          </div>
        </Section>
      )}
      {card.files.length > 0 && (
        <Section title={`Files · ${card.files.length}`}>
          <ul className="grid gap-4">
            {card.files.map((p) => (
              <FileRow key={p} path={p} onOpenCode={onOpenCode} />
            ))}
          </ul>
        </Section>
      )}
      {tests.length > 0 && (
        <Section title="Covered by">
          <Refs>
            {tests.map((t) => (
              <CodeRef key={`${t.path}:${t.line}`} meta={testMeta(t)} text={t.title} onOpen={() => onOpenCode(t.path, refTarget(t))} />
            ))}
          </Refs>
        </Section>
      )}
    </>
  )
}

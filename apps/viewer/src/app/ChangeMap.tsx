import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AnimatePresence } from 'motion/react'
import { graphModel, groupById, groupOf, highlightFor, resolveSelection, sourceLine, useMap, type Selection } from '@/data'
import { AttentionDetail } from '@/features/attention'
import { CardDetail, GroupDetail } from '@/features/cards'
import { CodePanel, type CodeTarget } from '@/features/code'
import { FlowDetail } from '@/features/flows'
import { Graph, ScopeBar, type GraphHandle, type Insets } from '@/features/graph'
import { CommandMenu } from '@/features/search'
import { IndexView, Sheet, type IndexTab } from '@/features/sheet'
import { Toolbar, type Theme } from '@/features/toolbar'
import { useMedia } from '@/shared/lib/use-media'
import { usePersistentState } from '@/shared/lib/use-persistent-state'
import { useWindowHeight, useWindowWidth } from '@/shared/lib/use-window-size'

const SHEET_W = 392
const GAP = 12
const TABS = ['flows', 'attention'] as const
const TECH = ['off', 'on'] as const

/** Layout shell: full-bleed canvas with floating sheet, code panel, toolbar and search, and the state they share. */
export function ChangeMap({ theme, onTheme }: { theme: Theme; onTheme: (theme: Theme) => void }) {
  const index = useMap()
  const { map } = index
  const graph = useRef<GraphHandle>(null)
  const wide = useMedia('(min-width: 768px)')
  const vw = useWindowWidth()
  const vh = useWindowHeight()
  const [selection, setSelection] = useState<Selection | null>(null)
  const [scope, setScope] = useState<string | null>(null)
  const [code, setCode] = useState<CodeTarget | null>(null)
  const [sheetOpen, setSheetOpen] = useState(true)
  const [search, setSearch] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [tab, setTab] = usePersistentState<IndexTab>('harness-map:tab', 'flows', TABS)
  const [tech, setTech] = usePersistentState('harness-map:technical', 'off', TECH)

  useEffect(() => {
    document.title = map.title
  }, [map.title])

  const model = useMemo(() => graphModel(index, scope), [index, scope])
  const resolved = useMemo(() => resolveSelection(index, selection), [index, selection])
  const highlight = useMemo(() => highlightFor(index, model, resolved), [index, model, resolved])

  useEffect(() => {
    // keep the selection's cards in view; a clicked card stays where it is
    if (resolved && resolved.kind !== 'card' && highlight) graph.current?.focus([...highlight.nodes])
  }, [resolved, highlight])

  const select = useCallback((s: Selection | null) => {
    setSelection(s)
    setSheetOpen(true)
  }, [])

  const focusCard = useCallback(
    (id: string) => {
      const card = index.cards.get(id)
      if (!card) return
      if (index.grouped) setScope(groupOf(index, card))
      select({ kind: 'card', id })
      requestAnimationFrame(() => graph.current?.focus([id]))
    },
    [index, select],
  )

  const onNodeClick = useCallback(
    (id: string) => {
      if (index.grouped && !model.scope) {
        setScope(id)
        select({ kind: 'group', id })
      } else {
        setSelection((s) => (s?.kind === 'card' && s.id === id ? null : { kind: 'card', id }))
        setSheetOpen(true)
      }
    },
    [index, model.scope, select],
  )

  const openCode = useCallback(
    (path: string, target: string | null = null) => setCode((c) => ({ path, target, jump: (c?.jump ?? 0) + 1 })),
    [],
  )
  const leaveScope = useCallback(() => {
    setScope(null)
    setSelection((s) => (s?.kind === 'group' ? null : s))
  }, [])

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearch((v) => !v)
        return
      }
      if (search || (e.target instanceof Element && e.target.closest('input, textarea, [cmdk-root]'))) return
      if (e.key === 'Escape') {
        if (code) setCode(null)
        else if (selection) setSelection(null)
        else if (model.scope) leaveScope()
      }
      if (resolved?.kind === 'flow' && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
        const step = resolved.step + (e.key === 'ArrowRight' ? 1 : -1)
        if (step >= 0 && step < resolved.flow.steps.length) setSelection({ kind: 'flow', id: resolved.flow.id, step })
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [code, selection, resolved, search, model.scope, leaveScope])

  const codeW = Math.min(780, vw * 0.46)
  const insets: Insets = wide
    ? { left: sheetOpen ? SHEET_W + GAP * 2 : 0, right: code ? codeW + GAP * 2 : 0, top: 0, bottom: 56 }
    : { left: 0, right: 0, top: 0, bottom: sheetOpen ? vh * 0.52 : 0 }

  const back = () => setSelection(null)
  let body: ReactNode
  let viewKey = 'index'
  if (!resolved) {
    body = <IndexView tab={tab} onTab={setTab} onSelect={select} onOpenCode={openCode} />
  } else if (resolved.kind === 'card') {
    viewKey = `card-${resolved.card.id}`
    body = <CardDetail card={resolved.card} onSelectCard={focusCard} onSelect={select} onOpenCode={openCode} />
  } else if (resolved.kind === 'group') {
    viewKey = `group-${resolved.group.id}`
    body = <GroupDetail group={resolved.group} cards={resolved.cards} onSelectCard={focusCard} />
  } else if (resolved.kind === 'attention') {
    viewKey = `attention-${resolved.point.id}`
    body = <AttentionDetail point={resolved.point} onSelectCard={focusCard} onOpenCode={openCode} />
  } else {
    const { flow, step } = resolved
    viewKey = `flow-${flow.id}`
    body = (
      <FlowDetail
        flow={flow}
        step={step}
        onStep={(s) => select({ kind: 'flow', id: flow.id, step: s })}
        showTech={tech === 'on'}
        onShowTech={(open) => setTech(open ? 'on' : 'off')}
        onSelectCard={focusCard}
        onOpenCode={openCode}
      />
    )
  }

  return (
    <div className="relative h-full overflow-hidden bg-canvas">
      <div className="absolute inset-0">
        <Graph
          key={model.key}
          ref={graph}
          nodes={model.nodes}
          edges={model.edges}
          highlight={highlight}
          insets={insets}
          onNodeClick={onNodeClick}
          onPaneClick={back}
          onZoom={setZoom}
        />
      </div>
      <AnimatePresence>
        {model.scope && (
          <ScopeBar
            key="scope"
            title={groupById(index, model.scope)?.title ?? model.scope}
            left={wide ? insets.left + GAP : 8}
            onExit={leaveScope}
          />
        )}
      </AnimatePresence>
      <Sheet open={sheetOpen} title={map.title} subtitle={sourceLine(map)} viewKey={viewKey} onBack={resolved ? back : undefined}>
        {body}
      </Sheet>
      <AnimatePresence>{code && <CodePanel key="code" {...code} onClose={() => setCode(null)} />}</AnimatePresence>
      <Toolbar
        canvas={graph}
        zoom={zoom}
        sheetOpen={sheetOpen}
        onToggleSheet={() => setSheetOpen((v) => !v)}
        onSearch={() => setSearch(true)}
        theme={theme}
        onTheme={onTheme}
        right={code && wide ? codeW + GAP * 2 : GAP}
      />
      <CommandMenu open={search} onOpenChange={setSearch} onSelectCard={focusCard} onSelect={select} onOpenFile={openCode} />
    </div>
  )
}

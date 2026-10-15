import type { HarnessMap, MapAttention, MapCard, MapCode, MapCodeRef, MapFlow, MapGroup, MapNote, MapTest, MapTestRef } from './map.v1'

/** Above this many cards the canvas shows modules first and cards on drill-in. */
export const GROUP_THRESHOLD = 40

/** A canvas edge: from caller to dependency. */
export type Link = [from: string, to: string]

export type Selection =
  | { kind: 'card'; id: string }
  | { kind: 'group'; id: string }
  | { kind: 'flow'; id: string; step: number }
  | { kind: 'attention'; id: string }

export interface MapIndex {
  map: HarnessMap
  cards: Map<string, MapCard>
  groups: Map<string, MapGroup>
  links: Link[]
  /** Outgoing (dependencies) and incoming (callers) card ids. */
  out: Map<string, string[]>
  in: Map<string, string[]>
  /** Colour slot of a layer: its position in the declared order. */
  layerSlot: (layerId: string) => number
  layerTitle: (layerId: string) => string
  grouped: boolean
}

const OTHER_GROUP: MapGroup = { id: '~other', title: 'Other' }

export function indexMap(map: HarnessMap): MapIndex {
  const cards = new Map(map.cards.map((c) => [c.id, c]))
  const links: Link[] = map.edges.map((e) => [e.from, e.to])
  const out = new Map<string, string[]>(map.cards.map((c) => [c.id, []]))
  const inn = new Map<string, string[]>(map.cards.map((c) => [c.id, []]))
  links.forEach(([a, b]) => {
    out.get(a)?.push(b)
    inn.get(b)?.push(a)
  })
  const slots = new Map(map.layers.map((l, i) => [l.id, i]))
  const titles = new Map(map.layers.map((l) => [l.id, l.title]))
  const groups = new Map(map.groups.map((g) => [g.id, g]))
  return {
    map,
    cards,
    groups,
    links,
    out,
    in: inn,
    layerSlot: (id) => slots.get(id) ?? 0,
    layerTitle: (id) => titles.get(id) ?? id,
    grouped: groups.size > 0 && map.cards.length > GROUP_THRESHOLD,
  }
}

export const groupOf = (index: MapIndex, card: MapCard) => (card.group && index.groups.has(card.group) ? card.group : OTHER_GROUP.id)

/** Declared module, or the catch-all for cards without one. */
export const groupById = (index: MapIndex, id: string) => index.groups.get(id) ?? (id === OTHER_GROUP.id ? OTHER_GROUP : undefined)

/* ───────── Canvas model ───────── */

export interface GraphNode {
  id: string
  layer: number
  eyebrow: string
  title: string
  summary: string
}

export interface GraphModel {
  /** Changes when the visible structure changes, so the canvas lays out again. */
  key: string
  /** Module the canvas is drilled into, if any. */
  scope: string | null
  nodes: GraphNode[]
  links: Link[]
  /** Node that stands for a card in this model: the card itself, its module, or none when hidden. */
  nodeOf: (cardId: string) => string | undefined
}

const cardNode = (index: MapIndex, c: MapCard): GraphNode => ({
  id: c.id,
  layer: index.layerSlot(c.layer),
  eyebrow: index.layerTitle(c.layer),
  title: c.title,
  summary: c.summary,
})

/** What the canvas shows: every card, the modules of a large change, or the cards of one module
 * (an empty or unknown module falls back to the modules). */
export function graphModel(index: MapIndex, scope: string | null): GraphModel {
  const { map } = index
  if (!index.grouped) {
    return {
      key: signature(
        map.cards.map((c) => c.id),
        index.links,
      ),
      scope: null,
      nodes: map.cards.map((c) => cardNode(index, c)),
      links: index.links,
      nodeOf: (id) => (index.cards.has(id) ? id : undefined),
    }
  }
  const inScope = scope ? map.cards.filter((c) => groupOf(index, c) === scope) : []
  if (scope && inScope.length) {
    const ids = new Set(inScope.map((c) => c.id))
    const links = index.links.filter(([a, b]) => ids.has(a) && ids.has(b))
    return {
      key: `${scope}:${signature([...ids], links)}`,
      scope,
      nodes: inScope.map((c) => cardNode(index, c)),
      links,
      nodeOf: (id) => (ids.has(id) ? id : undefined),
    }
  }
  const members = new Map<string, MapCard[]>()
  map.cards.forEach((c) => {
    const g = groupOf(index, c)
    members.set(g, [...(members.get(g) ?? []), c])
  })
  const seen = new Set<string>()
  const links: Link[] = []
  index.links.forEach(([a, b]) => {
    const ga = groupOf(index, index.cards.get(a)!)
    const gb = groupOf(index, index.cards.get(b)!)
    if (ga !== gb && !seen.has(`${ga}>${gb}`)) {
      seen.add(`${ga}>${gb}`)
      links.push([ga, gb])
    }
  })
  const nodes = [...members].map(([id, cards]) => {
    const g = groupById(index, id) ?? OTHER_GROUP
    return {
      id,
      layer: dominantLayer(index, cards),
      eyebrow: `${cards.length} cards`,
      title: g.title,
      summary: g.summary ?? cards.map((c) => c.title).join(', '),
    }
  })
  return {
    key: `groups:${signature([...members.keys()], links)}`,
    scope: null,
    nodes,
    links,
    nodeOf: (id) => {
      const c = index.cards.get(id)
      return c && groupOf(index, c)
    },
  }
}

function dominantLayer(index: MapIndex, cards: MapCard[]) {
  const count = new Map<string, number>()
  cards.forEach((c) => count.set(c.layer, (count.get(c.layer) ?? 0) + 1))
  const [layer] = [...count].sort((a, b) => b[1] - a[1])[0] ?? ['']
  return index.layerSlot(layer)
}

const signature = (ids: string[], links: Link[]) =>
  `${[...ids].sort().join(',')}|${links
    .map(([a, b]) => `${a}>${b}`)
    .sort()
    .join(',')}`

/* ───────── Selection ───────── */

export type Resolved =
  | { kind: 'card'; card: MapCard }
  | { kind: 'group'; group: MapGroup; cards: MapCard[] }
  | { kind: 'flow'; flow: MapFlow; step: number }
  | { kind: 'attention'; point: MapAttention }

/** The entity a selection points at, or null once a live update removed it. */
export function resolveSelection(index: MapIndex, sel: Selection | null): Resolved | null {
  if (!sel) return null
  const { map } = index
  switch (sel.kind) {
    case 'card': {
      const card = index.cards.get(sel.id)
      return card ? { kind: 'card', card } : null
    }
    case 'group': {
      const group = groupById(index, sel.id)
      const cards = map.cards.filter((c) => groupOf(index, c) === sel.id)
      return group && cards.length ? { kind: 'group', group, cards } : null
    }
    case 'flow': {
      const flow = map.flows.find((f) => f.id === sel.id)
      return flow ? { kind: 'flow', flow, step: Math.max(0, Math.min(sel.step, flow.steps.length - 1)) } : null
    }
    case 'attention': {
      const point = map.attention.find((a) => a.id === sel.id)
      return point ? { kind: 'attention', point } : null
    }
  }
}

export interface Highlight {
  nodes: Set<string>
  primary?: string
  /** Flow steps animate the edges between their cards. */
  flow?: boolean
  edge: (a: string, b: string) => boolean
}

/** Canvas emphasis for a selection, expressed in the nodes of the current graph model. */
export function highlightFor(index: MapIndex, model: GraphModel, sel: Resolved | null): Highlight | null {
  if (!sel || sel.kind === 'group') return null
  if (sel.kind === 'card') {
    const primary = model.nodeOf(sel.card.id)
    if (!primary) return null
    const near = [...(index.in.get(sel.card.id) ?? []), ...(index.out.get(sel.card.id) ?? [])]
    const nodes = new Set([primary, ...near.map(model.nodeOf).filter((n) => n !== undefined)])
    return { nodes, primary, edge: (a, b) => a === primary || b === primary }
  }
  const stepCards = sel.kind === 'flow' ? sel.flow.steps[sel.step]?.cards : undefined
  const ids = sel.kind === 'attention' ? sel.point.cards : stepCards?.length ? stepCards : sel.flow.cards
  const nodes = new Set(ids.map(model.nodeOf).filter((n) => n !== undefined))
  if (!nodes.size) return null
  return { nodes, flow: sel.kind === 'flow' && sel.flow.steps.length > 0, edge: (a, b) => nodes.has(a) && nodes.has(b) }
}

/* ───────── Files, code and tests ───────── */

export function changeStats(map: HarnessMap) {
  const files = Object.values(map.files)
  const added = files.filter((f) => f.status === 'added').length
  return {
    files: files.length,
    added,
    changed: files.length - added,
    critical: map.attention.filter((a) => a.severity === 'critical').length,
  }
}

/** Mono line under the title: refs and size of the change. */
export function sourceLine(map: HarnessMap) {
  const { baseRef, headRef, base, head } = map.source
  const n = Object.keys(map.files).length
  return `${baseRef ?? base.slice(0, 7)}…${headRef ?? head.slice(0, 7)} · ${n} ${n === 1 ? 'file' : 'files'}`
}

export const linesLabel = (start: number, end?: number) => (end && end !== start ? `lines ${start}–${end}` : `line ${start}`)

export function refMeta(ref: MapCodeRef) {
  const where = ref.symbol ?? (ref.start ? linesLabel(ref.start, ref.end) : '')
  return where ? `${ref.path} · ${where}` : ref.path
}

/** Anchor inside the code panel: a hunk (`hunk-n`), a line (`L12`) or a range (`L12-20`). */
export function refTarget(ref: { start?: number; end?: number; line?: number }): string | null {
  const start = ref.start ?? ref.line
  if (!start) return null
  return ref.end && ref.end !== start ? `L${start}-${ref.end}` : `L${start}`
}

export const testMeta = (t: MapTestRef) => `${t.path}:${t.line}`

/** Symbol notes of one file, in line order. */
export const notesFor = (map: HarnessMap, path: string): MapNote[] =>
  map.notes.filter((n) => n.path === path).sort((a, b) => a.start - b.start || b.end - a.end)

/** Notes of a hunk, or the subjects of the commits that introduced it when no note covers it. */
export function hunkNote(map: HarnessMap, hunk: NonNullable<MapCode['hunks']>[number]): string | undefined {
  const notes = hunk.notes.flatMap((i) => map.notes[i]?.text ?? [])
  if (notes.length) return notes.join(' ')
  const subjects = hunk.commits.flatMap((sha) => map.commits[sha]?.subject ?? [])
  return subjects.length ? [...new Set(subjects)].join('; ') : undefined
}

/** Tests that prove a card: linked to its attention points or flows, or living in its files. */
export function testsFor(map: HarnessMap, card: MapCard): MapTest[] {
  const ids = new Set([...card.attention, ...card.flows])
  return map.tests.filter((t) => t.ids.some((id) => ids.has(id)) || card.files.includes(t.path))
}

import type { HarnessMap, MapCard } from './map.v1'
import { GROUP_THRESHOLD, graphModel, highlightFor, indexMap, resolveSelection } from './selectors'

function map(cardCount: number, groups = true): HarnessMap {
  const cards: MapCard[] = Array.from({ length: cardCount }, (_, i) => ({
    id: `c${i}`,
    layer: 'l',
    group: groups ? (i % 2 ? 'odd' : 'even') : undefined,
    title: `Card ${i}`,
    summary: '',
    files: [],
    attention: [],
    flows: [],
  }))
  return {
    format: 'harness-map-v1',
    title: 'Fixture',
    source: { repository: 'r', base: 'a'.repeat(40), head: 'b'.repeat(40) },
    layers: [{ id: 'l', title: 'Layer' }],
    groups: groups
      ? [
          { id: 'even', title: 'Even' },
          { id: 'odd', title: 'Odd' },
        ]
      : [],
    cards,
    // c0 → c1 crosses modules, c0 → c2 stays inside "even"
    edges: [
      { from: 'c0', to: 'c1', kind: 'import' },
      { from: 'c0', to: 'c2', kind: 'import' },
    ],
    files: {},
    notes: [],
    commits: {},
    attention: [],
    flows: [],
    tests: [],
    followups: [],
    runs: [],
    code: {},
  }
}

describe('canvas grouping', () => {
  it('shows every card up to the threshold', () => {
    expect(graphModel(indexMap(map(GROUP_THRESHOLD)), null).nodes).toHaveLength(GROUP_THRESHOLD)
  })

  it('shows modules above the threshold, with edges between modules only', () => {
    const model = graphModel(indexMap(map(GROUP_THRESHOLD + 1)), null)
    expect(model.nodes.map((n) => n.id)).toEqual(['even', 'odd'])
    expect(model.links).toEqual([['even', 'odd']])
    expect(model.nodeOf('c3')).toBe('odd')
  })

  it('drills into one module and falls back to modules for an unknown one', () => {
    const index = indexMap(map(GROUP_THRESHOLD + 1))
    const inside = graphModel(index, 'even')
    expect(inside.scope).toBe('even')
    expect(inside.nodes.every((n) => Number(n.id.slice(1)) % 2 === 0)).toBe(true)
    expect(inside.links).toEqual([['c0', 'c2']])
    expect(inside.nodeOf('c1')).toBeUndefined()
    expect(graphModel(index, 'gone').scope).toBeNull()
  })

  it('never groups a map without declared modules', () => {
    expect(indexMap(map(GROUP_THRESHOLD + 5, false)).grouped).toBe(false)
  })

  it('highlights the module that holds a selected card', () => {
    const index = indexMap(map(GROUP_THRESHOLD + 1))
    const hl = highlightFor(index, graphModel(index, null), resolveSelection(index, { kind: 'card', id: 'c0' }))
    expect(hl?.primary).toBe('even')
    expect([...(hl?.nodes ?? [])].sort()).toEqual(['even', 'odd'])
  })

  it('drops a selection whose target disappeared', () => {
    expect(resolveSelection(indexMap(map(3)), { kind: 'card', id: 'missing' })).toBeNull()
  })
})

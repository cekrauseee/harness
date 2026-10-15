/** From caller to dependency. */
export type Edge = [from: string, to: string]

// Layered top-down layout: rank = longest path from the sources, barycenter ordering to reduce
// crossings, then x pulled toward neighbours while keeping order and spacing.
export const NODE_W = 232

export type Point = { x: number; y: number }
export type Positions = Record<string, Point>
export type Heights = Record<string, number>

interface LayoutNode {
  id: string
  in: string[]
  out: string[]
  x: number
  b: number
  want: number
}

/** Dependency depth of each node; edges that close a cycle are ignored. */
export function ranks(ids: string[], edges: Edge[]): Record<string, number> {
  const inn: Record<string, string[]> = Object.fromEntries(ids.map((id) => [id, []]))
  edges.forEach(([a, b]) => inn[b]?.push(a))
  const rank: Record<string, number> = {}
  const visiting = new Set<string>()
  const rankOf = (id: string): number => {
    if (rank[id] !== undefined) return rank[id]
    if (visiting.has(id)) return -1
    visiting.add(id)
    const r = Math.max(-1, ...(inn[id] ?? []).map(rankOf)) + 1
    visiting.delete(id)
    return (rank[id] = r)
  }
  ids.forEach(rankOf)
  return rank
}

export function computeLayout(ids: string[], edges: Edge[], heights: Heights, { gapX = 64, gapY = 88 } = {}): Positions {
  const g: Record<string, LayoutNode> = Object.fromEntries(ids.map((id) => [id, { id, in: [], out: [], x: 0, b: 0, want: 0 }]))
  edges.forEach(([a, b]) => {
    g[a]?.out.push(b)
    g[b]?.in.push(a)
  })
  const rank = ranks(ids, edges)
  const rows: LayoutNode[][] = []
  ids.forEach((id) => (rows[rank[id]!] ??= []).push(g[id]!))
  const dense = rows.filter(Boolean)
  const step = NODE_W + gapX
  const spread = (row: LayoutNode[]) =>
    row.forEach((n, i) => {
      n.x = (i - (row.length - 1) / 2) * step
    })
  const mean = (list: string[], fallback: number) => (list.length ? list.reduce((s, id) => s + g[id]!.x, 0) / list.length : fallback)
  dense.forEach(spread)
  for (let it = 0; it < 24; it++) {
    const down = it % 2 === 0
    for (const row of down ? dense.slice(1) : dense.slice(0, -1).reverse()) {
      row.forEach((n) => {
        n.b = mean(down ? n.in : n.out, n.x)
      })
      row.sort((a, b) => a.b - b.b)
      spread(row)
    }
  }
  for (let it = 0; it < 60; it++) {
    for (const row of it % 2 ? [...dense].reverse() : dense) {
      row.forEach((n) => {
        n.want = mean([...n.in, ...n.out], n.x)
        n.x = (n.x + n.want) / 2
      })
      for (let i = 1; i < row.length; i++) row[i]!.x = Math.max(row[i]!.x, row[i - 1]!.x + step)
      const shift = row.reduce((s, n) => s + n.want - n.x, 0) / row.length
      row.forEach((n) => {
        n.x += shift
      })
    }
  }
  const pos: Positions = {}
  let y = 0
  dense.forEach((row) => {
    const h = Math.max(...row.map((n) => heights[n.id] ?? 0))
    row.forEach((n) => {
      pos[n.id] = { x: n.x, y: y + (h - (heights[n.id] ?? 0)) / 2 }
    })
    y += h + gapY
  })
  const minX = Math.min(...Object.values(pos).map((p) => p.x))
  Object.values(pos).forEach((p) => {
    p.x -= minX
  })
  return pos
}

/** Port offsets: outgoing edges spread along the card's bottom, incoming along its top, ordered by
 * the other end's x so parallel edges do not cross at the card. */
export function portOffsets(edges: Edge[], pos: Positions): Record<string, { s: number; t: number }> {
  const outs: Record<string, string[]> = {}
  const ins: Record<string, string[]> = {}
  edges.forEach(([a, b]) => {
    ;(outs[a] ??= []).push(b)
    ;(ins[b] ??= []).push(a)
  })
  const off = (list: string[], other: string) => {
    const sorted = [...list].sort((p, q) => pos[p]!.x - pos[q]!.x)
    const gap = Math.min(22, (NODE_W - 64) / Math.max(sorted.length - 1, 1))
    return (sorted.indexOf(other) - (sorted.length - 1) / 2) * gap
  }
  return Object.fromEntries(edges.map(([a, b]) => [`${a}>${b}`, { s: off(outs[a]!, b), t: off(ins[b]!, a) }]))
}

export function bounds(ids: string[], pos: Positions, heights: Heights) {
  const xs = ids.map((id) => pos[id]!.x)
  const ys = ids.map((id) => pos[id]!.y)
  return {
    x0: Math.min(...xs) - NODE_W / 2,
    x1: Math.max(...xs) + NODE_W / 2,
    y0: Math.min(...ys),
    y1: Math.max(...ids.map((id) => pos[id]!.y + (heights[id] ?? 0))),
  }
}

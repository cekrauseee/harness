import { hunkNote, notesFor, type HarnessMap, type MapCode } from '@/data'

export type RowKind = ' ' | '+' | '-'

export interface Row {
  kind: RowKind
  oldLine?: number
  newLine?: number
  text: string
}

export interface Block {
  /** Anchor for references: `hunk-n` or the note's `L<start>-<end>`. */
  id?: string
  head: string
  note?: string
  rows: Row[]
}

const commitSubjects = (map: HarnessMap, shas: string[] = []) => {
  const subjects = shas.flatMap((sha) => map.commits[sha]?.subject ?? [])
  return subjects.length ? [...new Set(subjects)].join('; ') : undefined
}

/** Rows of a unified diff hunk, numbered from its starts; "\ No newline" markers are dropped. */
export function hunkRows(lines: string[], oldStart: number, newStart: number): Row[] {
  let o = oldStart
  let n = newStart
  return lines.flatMap((line): Row[] => {
    const kind = line[0]
    const text = line.slice(1)
    if (kind === '+') return [{ kind, newLine: n++, text }]
    if (kind === '-') return [{ kind, oldLine: o++, text }]
    if (kind === ' ') return [{ kind, oldLine: o++, newLine: n++, text }]
    return []
  })
}

/** Blocks to render: a new file split by its symbol notes (gaps stay visible), a changed file by hunk. */
export function codeBlocks(map: HarnessMap, path: string, code: MapCode): { single: boolean; blocks: Block[] } {
  if (code.hunks) {
    return {
      single: false,
      blocks: code.hunks.map((h, i) => ({
        id: `hunk-${i}`,
        head: `Change ${i + 1}${h.context ? ` · ${h.context}` : ''}`,
        note: hunkNote(map, h),
        rows: hunkRows(h.lines, h.oldStart, h.newStart),
      })),
    }
  }
  const lines = code.lines ?? []
  const total = lines.length
  const rows = (a: number, b: number): Row[] => lines.slice(a - 1, b).map((text, i) => ({ kind: ' ', newLine: a + i, text }))
  const out: Block[] = []
  let pos = 1
  // shortcut: a note nested inside an earlier one (a method inside its class) is skipped; show nested notes when maps start using them.
  for (const s of notesFor(map, path)) {
    if (s.start < pos || s.start > total) continue
    const end = Math.min(s.end, total)
    if (s.start > pos) out.push({ head: `Lines ${pos}–${s.start - 1}`, rows: rows(pos, s.start - 1) })
    out.push({ id: `L${s.start}-${s.end}`, head: `Lines ${s.start}–${end} · ${s.symbol}`, note: s.text, rows: rows(s.start, end) })
    pos = end + 1
  }
  if (pos <= total) out.push({ head: pos === 1 ? `${total} lines` : `Lines ${pos}–${total}`, rows: rows(pos, total) })
  if (out.length === 1 && !out[0]!.note) out[0]!.note = commitSubjects(map, code.commits)
  return { single: true, blocks: out }
}

export const OMITTED: Record<NonNullable<MapCode['omitted']>, string> = {
  binary: 'Binary file: no textual content to show.',
  excluded: 'Excluded from the map.',
  'too-large': 'Too large to show.',
}

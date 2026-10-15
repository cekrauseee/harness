import { bundledLanguages, createHighlighter, type BundledLanguage, type HighlighterGeneric } from 'shiki'
import type { Row } from './blocks'

type Lang = BundledLanguage | 'text'

/** Language from the file extension (or name, e.g. Dockerfile); unknown files stay plain text. */
export function langOf(path: string): Lang {
  const ext = (path.split('/').pop() ?? '').toLowerCase().split('.').pop() ?? ''
  return ext in bundledLanguages ? (ext as BundledLanguage) : 'text'
}

let highlighter: Promise<HighlighterGeneric<BundledLanguage, 'github-light' | 'github-dark'>> | undefined
const loaded = new Set<Lang>()

async function get(lang: Lang) {
  highlighter ??= createHighlighter({ themes: ['github-light', 'github-dark'], langs: [] })
  const h = await highlighter
  if (lang !== 'text' && !loaded.has(lang)) {
    await h.loadLanguage(lang)
    loaded.add(lang)
  }
  return h
}

/** Highlights lines as one block (multi-line strings and comments stay correct) and returns per-line HTML.
 * Dual themes: tokens carry --shiki-light / --shiki-dark, chosen in CSS by the .dark class. */
export async function highlightLines(lines: string[], lang: Lang): Promise<string[]> {
  if (!lines.length) return []
  const h = await get(lang)
  const html = h.codeToHtml(lines.join('\n'), { lang, themes: { light: 'github-light', dark: 'github-dark' }, defaultColor: false })
  const tpl = document.createElement('template')
  tpl.innerHTML = html
  return [...tpl.content.querySelectorAll('.line')].map((l) => l.innerHTML)
}

/** Diff hunk: highlights the new side (context + added) and the old side (context + removed) separately. */
export async function highlightHunk(rows: Row[], lang: Lang): Promise<string[]> {
  const [newSide, oldSide] = await Promise.all([
    highlightLines(
      rows.filter((r) => r.kind !== '-').map((r) => r.text),
      lang,
    ),
    highlightLines(
      rows.filter((r) => r.kind !== '+').map((r) => r.text),
      lang,
    ),
  ])
  let ni = 0
  let oi = 0
  return rows.map(({ kind }) => {
    if (kind === '-') return oldSide[oi++] ?? ''
    if (kind === ' ') oi++
    return newSide[ni++] ?? ''
  })
}

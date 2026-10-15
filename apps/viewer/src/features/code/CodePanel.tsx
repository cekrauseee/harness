import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { X } from 'lucide-react'
import { useMap } from '@/data'
import { StatusBadge } from '@/shared/blocks'
import { EASE, Item, Stagger, prefersReducedMotion } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { ScrollArea } from '@/shared/ui/scroll-area'
import { OMITTED, codeBlocks } from './blocks'
import { highlightHunk, highlightLines, langOf } from './shiki'

const esc = (s: string) => s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]!)

export interface CodeTarget {
  path: string
  /** `hunk-n`, `L<line>` or `L<start>-<end>`. */
  target?: string | null
  /** Bumped on every open, so opening the same target again scrolls and flashes again. */
  jump: number
}

/** Elements a target points at: a block whose anchor matches (a hunk, an explained section), otherwise the referenced lines. */
function targetElements(root: HTMLElement, target: string): { block: HTMLElement | null; elements: HTMLElement[] } {
  const block = root.querySelector<HTMLElement>(`#${CSS.escape(target)}`)
  if (block) return { block, elements: [block] }
  const [, from, to] = /^L(\d+)(?:-(\d+))?$/.exec(target) ?? []
  if (!from) return { block: null, elements: [] }
  const elements = [...root.querySelectorAll<HTMLElement>('[data-n]')].filter((r) => {
    const n = Number(r.dataset.n)
    return n >= Number(from) && n <= Number(to ?? from)
  })
  return { block: null, elements }
}

// One file's content. Keyed by path, so switching files cross-fades; jumps inside a file scroll smoothly.
function CodeBody({ path, target, jump }: CodeTarget) {
  const { map } = useMap()
  const root = useRef<HTMLDivElement>(null)
  const lang = langOf(path)
  const fileCode = map.code[path]
  const file = map.files[path]
  const shown = useMemo(() => (fileCode && !fileCode.omitted ? codeBlocks(map, path, fileCode) : null), [map, path, fileCode])
  const [html, setHtml] = useState<string[][] | null>(null)

  useEffect(() => {
    if (!shown || !fileCode) return
    let alive = true
    const work = shown.single
      ? highlightLines(fileCode.lines ?? [], lang).then((lines) =>
          shown.blocks.map((b) => b.rows.map((r) => lines[(r.newLine ?? 0) - 1] ?? '')),
        )
      : Promise.all(shown.blocks.map((b) => highlightHunk(b.rows, lang)))
    work.then(
      (h) => alive && setHtml(h),
      () => {},
    )
    return () => {
      alive = false
    }
  }, [shown, fileCode, lang])

  const first = useRef(true)
  const flashed = useRef<number | null>(null)
  const highlighted = html !== null
  useLayoutEffect(() => {
    const el = root.current
    const vp = el?.closest<HTMLElement>('[data-slot="scroll-area-viewport"]')
    if (!el || !vp) return
    if (!target) {
      if (first.current) vp.scrollTop = 0
      first.current = false
      return
    }
    const { block, elements } = targetElements(el, target)
    if (!elements[0]) return
    const prev = block?.previousElementSibling as HTMLElement | null | undefined
    const anchor = block ? (prev?.dataset.note !== undefined ? prev : block) : elements[0]
    const top = vp.scrollTop + anchor.getBoundingClientRect().top - vp.getBoundingClientRect().top - (block ? 12 : 96)
    vp.scrollTo({ top, behavior: first.current || prefersReducedMotion() ? 'auto' : 'smooth' })
    first.current = false
    if (flashed.current === jump) return // re-run after highlighting: keep position, don't flash twice
    flashed.current = jump
    elements.forEach((e) => e.classList.remove('flash'))
    void elements[0].offsetWidth
    elements.forEach((e) => e.classList.add('flash'))
  }, [target, jump, highlighted])

  return (
    <motion.div
      ref={root}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.12 } }}
      transition={{ duration: 0.25, ease: EASE }}
    >
      <Stagger gap={0.05} delay={0.06} className="px-5 pb-8">
        {file?.role && (
          <Item as="p" className="mt-4 max-w-[68ch] text-[13px] leading-relaxed text-muted-foreground">
            {file.role}
          </Item>
        )}
        {!shown && (
          <Item as="p" className="mt-4 text-[13px] text-muted-foreground">
            {fileCode?.omitted ? OMITTED[fileCode.omitted] : 'No code in the map for this file.'}
          </Item>
        )}
        {shown?.blocks.map((b, k) => (
          <Item key={k}>
            {b.note && (
              <p data-note className="mt-6 mb-2 max-w-[72ch] border-l-2 border-brand pl-3 text-[12.5px] leading-relaxed">
                {b.note}
              </p>
            )}
            <div id={b.id} className="cm-code cm-block mt-3 overflow-clip rounded-xl border bg-background">
              <div className="sticky top-0 z-10 truncate border-b bg-secondary/90 px-3 py-1.5 font-mono text-[11px] text-muted-foreground backdrop-blur">
                {b.head}
              </div>
              <div className="overflow-x-auto">
                <div className="grid w-max min-w-full">
                  {b.rows.map((r, j) => (
                    <div
                      key={j}
                      data-n={r.kind !== '-' ? r.newLine : undefined}
                      className={cn(
                        'cm-line grid',
                        shown.single ? 'grid-cols-[52px_auto]' : 'grid-cols-[44px_44px_auto]',
                        r.kind === '+' && 'add',
                        r.kind === '-' && 'del',
                      )}
                    >
                      {!shown.single && (
                        <span
                          className={cn('pr-2.5 text-right text-muted-foreground/60 select-none', r.kind === '-' && 'text-destructive')}
                        >
                          {r.oldLine ?? ''}
                        </span>
                      )}
                      <span className={cn('pr-2.5 text-right text-muted-foreground/60 select-none', r.kind === '+' && 'text-ok')}>
                        {r.newLine ?? ''}
                      </span>
                      <span
                        className="tok pr-4 pl-1.5 whitespace-pre"
                        dangerouslySetInnerHTML={{ __html: html?.[k]?.[j] || esc(r.text) || ' ' }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Item>
        ))}
      </Stagger>
    </motion.div>
  )
}

export function CodePanel({ path, target, jump, onClose }: CodeTarget & { onClose: () => void }) {
  const file = useMap().map.files[path]
  const i = path.lastIndexOf('/')
  return (
    <motion.aside
      aria-label="Code"
      initial={{ opacity: 0, x: 32 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 32 }}
      transition={{ type: 'spring', stiffness: 380, damping: 40 }}
      className="cm-float absolute top-3 right-3 bottom-3 z-20 flex w-[min(780px,46vw)] flex-col overflow-hidden rounded-[14px] border will-change-transform max-md:inset-2 max-md:w-auto"
    >
      <header className="flex items-start justify-between gap-3 border-b py-3 pr-3 pl-5">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={path}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -3 }}
            transition={{ duration: 0.16 }}
            className="flex min-w-0 flex-col gap-1"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span className="truncate font-mono text-[13px] font-semibold">{path.slice(i + 1)}</span>
              <StatusBadge file={file} />
            </div>
            <span className="font-mono text-[11px] [overflow-wrap:anywhere] text-muted-foreground">
              {path.slice(0, i + 1)}
              {file?.previous && ` · from ${file.previous}`}
            </span>
          </motion.div>
        </AnimatePresence>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close code">
          <X />
        </Button>
      </header>
      <ScrollArea className="min-h-0 flex-1 select-text">
        <AnimatePresence mode="wait" initial={false}>
          <CodeBody key={path} path={path} target={target} jump={jump} />
        </AnimatePresence>
      </ScrollArea>
    </motion.aside>
  )
}

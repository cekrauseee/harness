import { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState, type PointerEvent, type Ref } from 'react'
import type { GraphNode, Highlight, Link as Edge } from '@/data'
import { LayerDot } from '@/shared/blocks'
import { prefersReducedMotion } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { NODE_W, bounds, computeLayout, portOffsets, ranks, type Heights, type Positions } from './layout'

export interface GraphHandle {
  fit: () => void
  focus: (ids: string[]) => void
  zoomIn: () => void
  zoomOut: () => void
  resetZoom: () => void
  relayout: () => void
}

/** Space covered by floating panels; fit and focus frame only what stays visible. */
export interface Insets {
  left: number
  right: number
  top: number
  bottom: number
}

interface View {
  x: number
  y: number
  k: number
}

interface Props {
  ref?: Ref<GraphHandle>
  nodes: GraphNode[]
  edges: Edge[]
  highlight: Highlight | null
  insets: Insets
  onNodeClick: (id: string) => void
  onPaneClick: () => void
  onZoom: (k: number) => void
}

const MARGIN = 48
const clampK = (k: number) => Math.min(2, Math.max(0.3, k))
const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)

function visibleArea(el: HTMLElement, i: Insets) {
  const r = el.getBoundingClientRect()
  return { x: i.left + MARGIN, y: i.top + MARGIN, w: r.width - i.left - i.right - 2 * MARGIN, h: r.height - i.top - i.bottom - 2 * MARGIN }
}

/** Entrance cascade: top-down by dependency depth, left to right within a row. */
function cascadeDelays(ids: string[], edges: Edge[], pos: Positions) {
  const rank = ranks(ids, edges)
  const rows: Record<number, string[]> = {}
  ids.forEach((id) => (rows[rank[id]!] ??= []).push(id))
  const delays: Record<string, number> = {}
  Object.entries(rows).forEach(([r, row]) =>
    row
      .sort((a, b) => pos[a]!.x - pos[b]!.x)
      .forEach((id, i) => {
        delays[id] = Number(r) * 90 + i * 35
      }),
  )
  return delays
}

// Own canvas: pan, zoom, drag, animated layout. Positions are tweened with rAF so edges follow cards.
// It lays out once per mount; the parent remounts it when the visible structure changes.
export function Graph({ ref, nodes, edges, highlight, insets, onNodeClick, onPaneClick, onZoom }: Props) {
  const vp = useRef<HTMLDivElement>(null)
  const cards = useRef<Record<string, HTMLDivElement | null>>({})
  const raf = useRef(0)
  const glideTimer = useRef(0)
  const [measured, setMeasured] = useState<{ heights: Heights; delays: Record<string, number> } | null>(null)
  const [pos, setPos] = useState<Positions | null>(null)
  const [view, setView] = useState<View>({ x: 0, y: 0, k: 1 })
  const [gliding, setGliding] = useState(false)
  const [dragging, setDragging] = useState(false)
  const ids = useMemo(() => nodes.map((n) => n.id), [nodes])
  const heights = measured?.heights
  const delays = measured?.delays

  // Latest values for handlers that outlive a render (rAF ticks, wheel, imperative calls).
  const live = useRef({ pos, heights, view, insets, ids, edges })
  useLayoutEffect(() => {
    live.current = { pos, heights, view, insets, ids, edges }
  })

  useLayoutEffect(() => {
    if (measured) return
    const h = Object.fromEntries(ids.map((id) => [id, cards.current[id]?.offsetHeight || 84]))
    const p = computeLayout(ids, edges, h)
    setMeasured({ heights: h, delays: cascadeDelays(ids, edges, p) })
    setPos(p)
  }, [measured, ids, edges])

  useEffect(() => onZoom(view.k), [view.k, onZoom])

  const glide = useCallback((next: View, ms = 460) => {
    if (!prefersReducedMotion()) {
      setGliding(true)
      clearTimeout(glideTimer.current)
      glideTimer.current = window.setTimeout(() => setGliding(false), ms)
    }
    setView(next)
  }, [])

  const frame = useCallback(
    (targets: string[], { onlyIfHidden = false, smooth = true } = {}) => {
      const { pos: p, heights: h, view: v, insets: i } = live.current
      const el = vp.current
      const shown = targets.filter((id) => p?.[id])
      if (!p || !h || !el || !shown.length) return
      const b = bounds(shown, p, h)
      const a = visibleArea(el, i)
      const fitK = clampK(Math.min(1, a.w / (b.x1 - b.x0), a.h / (b.y1 - b.y0)))
      const set = smooth ? glide : setView
      if (onlyIfHidden) {
        const k = Math.min(v.k, fitK)
        const inside = v.x + b.x0 * k >= a.x && v.y + b.y0 * k >= a.y && v.x + b.x1 * k <= a.x + a.w && v.y + b.y1 * k <= a.y + a.h
        if (inside && k === v.k) return
        return set({ k, x: a.x + a.w / 2 - ((b.x0 + b.x1) / 2) * k, y: a.y + a.h / 2 - ((b.y0 + b.y1) / 2) * k })
      }
      set({
        k: fitK,
        x: a.x + (a.w - (b.x1 - b.x0) * fitK) / 2 - b.x0 * fitK,
        y: a.y + Math.max(0, (a.h - (b.y1 - b.y0) * fitK) / 2) - b.y0 * fitK,
      })
    },
    [glide],
  )

  const animateTo = useCallback((to: Positions, done?: () => void) => {
    cancelAnimationFrame(raf.current)
    const from = live.current.pos
    if (!from || prefersReducedMotion()) {
      setPos(to)
      return done?.()
    }
    const t0 = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / 560)
      const e = ease(t)
      const p: Positions = {}
      for (const id in to) {
        const a = from[id] ?? to[id]!
        p[id] = { x: a.x + (to[id]!.x - a.x) * e, y: a.y + (to[id]!.y - a.y) * e }
      }
      setPos(p)
      if (t < 1) raf.current = requestAnimationFrame(tick)
      else done?.()
    }
    raf.current = requestAnimationFrame(tick)
  }, [])

  const zoomAt = useCallback(
    (f: number, cx: number, cy: number, smooth: boolean) => {
      const v = live.current.view
      const k = clampK(v.k * f)
      const next = { k, x: cx - ((cx - v.x) * k) / v.k, y: cy - ((cy - v.y) * k) / v.k }
      if (smooth) glide(next, 260)
      else setView(next)
    },
    [glide],
  )

  useImperativeHandle(ref, () => {
    const zoomCentered = (f: number) => {
      if (!vp.current) return
      const a = visibleArea(vp.current, live.current.insets)
      zoomAt(f, a.x + a.w / 2, a.y + a.h / 2, true)
    }
    return {
      fit: () => frame(live.current.ids),
      focus: (targets) => frame(targets, { onlyIfHidden: true }),
      zoomIn: () => zoomCentered(1.2),
      zoomOut: () => zoomCentered(1 / 1.2),
      resetZoom: () => zoomCentered(1 / live.current.view.k),
      relayout: () => {
        const { ids: all, edges: e, heights: h } = live.current
        if (h) animateTo(computeLayout(all, e, h), () => frame(all))
      },
    }
  }, [frame, zoomAt, animateTo])

  // First fit once the canvas has a size (embedded viewers may mount hidden).
  const fitted = useRef(false)
  useEffect(() => {
    const el = vp.current
    if (!pos || fitted.current || !el) return
    const ro = new ResizeObserver(() => {
      if (fitted.current || !el.clientWidth) return
      fitted.current = true
      frame(live.current.ids, { smooth: false })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [pos, frame])

  useEffect(() => {
    const el = vp.current
    if (!el) return
    const z = { target: 1, cx: 0, cy: 0, raf: 0 }
    const easeZoom = () => {
      const v = live.current.view
      const k = Math.abs(z.target - v.k) < 0.001 || prefersReducedMotion() ? z.target : v.k + (z.target - v.k) * 0.22
      const next = { k, x: z.cx - ((z.cx - v.x) * k) / v.k, y: z.cy - ((z.cy - v.y) * k) / v.k }
      live.current.view = next
      setView(next)
      z.raf = k === z.target ? 0 : requestAnimationFrame(easeZoom)
    }
    const wheel = (e: WheelEvent) => {
      e.preventDefault()
      const r = el.getBoundingClientRect()
      if (!e.ctrlKey && !e.metaKey) return setView((v) => ({ ...v, x: v.x - e.deltaX, y: v.y - e.deltaY }))
      // Trackpad pinches send small continuous deltas: apply them directly. Mouse wheels send coarse
      // steps: ease toward the target so each notch glides instead of jumping.
      if (Math.abs(e.deltaY) < 40) {
        cancelAnimationFrame(z.raf)
        z.raf = 0
        return zoomAt(Math.exp(-e.deltaY * 0.01), e.clientX - r.left, e.clientY - r.top, false)
      }
      z.target = clampK((z.raf ? z.target : live.current.view.k) * Math.exp(-e.deltaY * 0.0022))
      z.cx = e.clientX - r.left
      z.cy = e.clientY - r.top
      z.raf ||= requestAnimationFrame(easeZoom)
    }
    el.addEventListener('wheel', wheel, { passive: false })
    return () => {
      el.removeEventListener('wheel', wheel)
      cancelAnimationFrame(z.raf)
    }
  }, [zoomAt])

  const drag = useRef<{ id?: string; x: number; y: number; moved: boolean } | null>(null)
  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return
    const card = (e.target as HTMLElement).closest<HTMLElement>('[data-node]')
    drag.current = { id: card?.dataset.node, x: e.clientX, y: e.clientY, moved: false }
    try {
      vp.current?.setPointerCapture(e.pointerId)
    } catch {
      /* synthetic pointer */
    }
  }
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    const dy = e.clientY - d.y
    if (!d.moved && Math.hypot(dx, dy) < 4) return
    if (!d.moved) {
      d.moved = true
      setDragging(true)
      cancelAnimationFrame(raf.current)
    }
    d.x = e.clientX
    d.y = e.clientY
    const id = d.id
    if (id) setPos((p) => p && { ...p, [id]: { x: p[id]!.x + dx / view.k, y: p[id]!.y + dy / view.k } })
    else setView((v) => ({ ...v, x: v.x + dx, y: v.y + dy }))
  }
  const onPointerUp = () => {
    const d = drag.current
    drag.current = null
    setDragging(false)
    if (!d || d.moved) return
    if (d.id) onNodeClick(d.id)
    else onPaneClick()
  }

  const paths = useMemo(() => {
    if (!pos || !heights) return []
    const off = portOffsets(edges, pos)
    return edges.map(([a, b]) => {
      const o = off[`${a}>${b}`]!
      const x1 = pos[a]!.x + o.s
      const y1 = pos[a]!.y + heights[a]!
      const x2 = pos[b]!.x + o.t
      const y2 = pos[b]!.y - 4
      const c = Math.max(36, (y2 - y1) * 0.5)
      return { a, b, d: `M${x1},${y1} C${x1},${y1 + c} ${x2},${y2 - c} ${x2},${y2}` }
    })
  }, [pos, heights, edges])
  const size = useMemo(() => (pos && heights && ids.length ? bounds(ids, pos, heights) : null), [pos, heights, ids])
  const hl = highlight

  return (
    <div
      ref={vp}
      className={cn('cm-canvas absolute inset-0 touch-none overflow-hidden', dragging ? 'cursor-grabbing' : 'cursor-grab')}
      style={{ backgroundPosition: `${view.x}px ${view.y}px`, backgroundSize: `${20 * view.k}px ${20 * view.k}px` }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div
        className={cn('cm-world absolute top-0 left-0 origin-top-left will-change-transform', gliding && 'gliding')}
        style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.k})` }}
      >
        <svg
          className="pointer-events-none absolute top-0 left-0 overflow-visible"
          width={size ? size.x1 + NODE_W : 0}
          height={size ? size.y1 + 200 : 0}
        >
          <defs>
            <marker id="cm-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,1 L9,5 L0,9 z" className="cm-arrow" />
            </marker>
            <marker id="cm-arrow-on" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,1 L9,5 L0,9 z" className="cm-arrow on" />
            </marker>
          </defs>
          {paths.map((p) => {
            const on = !!hl && hl.edge(p.a, p.b)
            return (
              <path
                key={`${p.a}>${p.b}`}
                d={p.d}
                className={cn('cm-edge', on && 'on', on && hl.flow && 'flowing', hl && !on && 'off')}
                style={on && hl.flow ? undefined : { animation: `cm-edge-in .6s ease ${(delays?.[p.b] ?? 0) + 160}ms both` }}
                markerEnd={on ? 'url(#cm-arrow-on)' : 'url(#cm-arrow)'}
              />
            )
          })}
        </svg>
        {nodes.map((n) => {
          const p = pos?.[n.id]
          const state = !hl ? null : hl.primary === n.id ? 'primary' : hl.nodes.has(n.id) ? 'on' : 'off'
          return (
            <div
              key={n.id}
              ref={(el) => {
                cards.current[n.id] = el
              }}
              data-node={n.id}
              role="button"
              tabIndex={0}
              aria-pressed={state === 'primary'}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onNodeClick(n.id)
                }
              }}
              style={{
                left: p ? p.x - NODE_W / 2 : 0,
                top: p ? p.y : 0,
                width: NODE_W,
                visibility: p ? 'visible' : 'hidden',
                animationDelay: `${delays?.[n.id] ?? 0}ms`,
              }}
              className={cn(
                'cm-node absolute rounded-[11px] border bg-card px-3.5 pt-[11px] pb-3 shadow-[var(--shadow-card)]',
                dragging ? 'cursor-grabbing' : 'cursor-pointer',
                'hover:-translate-y-px hover:shadow-[var(--shadow-hover)]',
                state === 'primary'
                  ? 'border-brand shadow-[0_0_0_4px_var(--brand-soft),var(--shadow-hover)] hover:shadow-[0_0_0_4px_var(--brand-soft),var(--shadow-hover)]'
                  : state === 'on'
                    ? 'border-[var(--brand-ring)] hover:border-brand'
                    : 'hover:border-foreground/15',
                state === 'off' && 'opacity-30',
              )}
            >
              <span className="cm-eyebrow flex items-center gap-1.5 text-[10px]">
                <LayerDot layer={n.layer} />
                {n.eyebrow}
              </span>
              <h3 className="mt-[5px] truncate text-[13px] font-semibold tracking-[-0.01em]">{n.title}</h3>
              <p className="mt-0.5 line-clamp-2 min-h-[2.8em] text-[11.5px] leading-[1.4] text-muted-foreground">{n.summary}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

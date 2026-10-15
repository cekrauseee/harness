import { useEffect, useState } from 'react'
import type { HarnessMap } from './map.v1'

// Served read-only by plugins/map-source.ts, which sends this event when the map folder changes.
const MAP_URL = '/map/map.json'
const CHANGED = 'harness-map:changed'

function isMap(value: unknown): value is HarnessMap {
  const v = value as Partial<HarnessMap> | null
  return v?.format === 'harness-map-v1' && typeof v.title === 'string' && Array.isArray(v.layers) && Array.isArray(v.cards)
}

// The consolidator validates maps against the schema; the viewer still tolerates a partial or older
// file: missing lists become empty and edges that point at unknown cards are dropped.
function normalize(raw: HarnessMap): HarnessMap {
  const map: HarnessMap = {
    ...raw,
    groups: raw.groups ?? [],
    edges: raw.edges ?? [],
    files: raw.files ?? {},
    notes: raw.notes ?? [],
    commits: raw.commits ?? {},
    attention: raw.attention ?? [],
    flows: raw.flows ?? [],
    tests: raw.tests ?? [],
    followups: raw.followups ?? [],
    runs: raw.runs ?? [],
    code: raw.code ?? {},
  }
  const ids = new Set(map.cards.map((c) => c.id))
  const seen = new Set<string>()
  map.edges = map.edges.filter(({ from, to }) => {
    const key = `${from}>${to}`
    if (from === to || !ids.has(from) || !ids.has(to) || seen.has(key)) return false
    seen.add(key)
    return true
  })
  return map
}

export async function fetchMap(): Promise<HarnessMap> {
  const res = await fetch(MAP_URL, { cache: 'no-store' })
  if (!res.ok) throw new Error(`map.json: HTTP ${res.status}`)
  const value: unknown = await res.json()
  if (!isMap(value)) throw new Error('map.json is not a harness-map-v1 map')
  return normalize(value)
}

export type MapState = { status: 'loading' } | { status: 'ready'; map: HarnessMap } | { status: 'failed'; error: string }

/** Loads the served map and reloads it whenever the folder changes; a failed reload keeps the last good map. */
export function useMapData(): MapState {
  const [state, setState] = useState<MapState>({ status: 'loading' })
  useEffect(() => {
    let alive = true
    let timer = 0
    const load = () =>
      fetchMap().then(
        (map) => alive && setState({ status: 'ready', map }),
        (e: unknown) => {
          if (!alive) return
          const error = e instanceof Error ? e.message : String(e)
          setState((s) => (s.status === 'ready' ? s : { status: 'failed', error }))
          console.warn(`Map not loaded: ${error}`)
        },
      )
    const onChange = () => {
      clearTimeout(timer)
      timer = window.setTimeout(load, 120)
    }
    void load()
    import.meta.hot?.on(CHANGED, onChange)
    return () => {
      alive = false
      clearTimeout(timer)
      import.meta.hot?.off(CHANGED, onChange)
    }
  }, [])
  return state
}

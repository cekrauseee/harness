import { createContext, use } from 'react'
import type { MapIndex } from './selectors'

export const MapContext = createContext<MapIndex | null>(null)

export function useMap(): MapIndex {
  const index = use(MapContext)
  if (!index) throw new Error('useMap needs a MapContext provider')
  return index
}

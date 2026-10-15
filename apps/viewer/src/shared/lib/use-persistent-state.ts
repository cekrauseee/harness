import { useCallback, useState } from 'react'
import { storage } from './storage'

/** A string preference remembered per browser; stored values outside `allowed` fall back. */
export function usePersistentState<T extends string>(key: string, fallback: T, allowed: readonly T[]): [T, (value: T) => void] {
  const [value, setValue] = useState(() => {
    const stored = storage.get(key, fallback) as T
    return allowed.includes(stored) ? stored : fallback
  })
  const set = useCallback(
    (next: T) => {
      setValue(next)
      storage.set(key, next)
    },
    [key],
  )
  return [value, set]
}

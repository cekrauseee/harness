import { useSyncExternalStore } from 'react'

const subscribe = (notify: () => void) => {
  window.addEventListener('resize', notify)
  return () => window.removeEventListener('resize', notify)
}

export const useWindowWidth = () => useSyncExternalStore(subscribe, () => window.innerWidth)
export const useWindowHeight = () => useSyncExternalStore(subscribe, () => window.innerHeight)

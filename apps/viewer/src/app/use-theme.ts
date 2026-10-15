import { useEffect } from 'react'
import type { Theme } from '@/features/toolbar'
import { useMedia } from '@/shared/lib/use-media'
import { usePersistentState } from '@/shared/lib/use-persistent-state'

const THEMES = ['system', 'light', 'dark'] as const

/** System → Light → Dark, remembered per browser; follows the system by default. */
export function useTheme() {
  const [theme, setTheme] = usePersistentState<Theme>('harness-map:theme', 'system', THEMES)
  const systemDark = useMedia('(prefers-color-scheme: dark)')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark' || (theme === 'system' && systemDark))
  }, [theme, systemDark])
  return [theme, setTheme] as const
}

import { useMemo } from 'react'
import { MotionConfig } from 'motion/react'
import { MapContext, indexMap, useMapData } from '@/data'
import { TooltipProvider } from '@/shared/ui/tooltip'
import { ChangeMap } from './ChangeMap'
import { useTheme } from './use-theme'

export function App() {
  const state = useMapData()
  const [theme, setTheme] = useTheme()
  const index = useMemo(() => (state.status === 'ready' ? indexMap(state.map) : null), [state])
  if (!index) {
    return (
      <div className="grid h-full place-items-center bg-canvas px-6 text-center text-sm text-muted-foreground">
        {state.status === 'failed' ? `Could not load the map: ${state.error}` : 'Loading…'}
      </div>
    )
  }
  return (
    <MapContext value={index}>
      <TooltipProvider delayDuration={350}>
        <MotionConfig reducedMotion="user">
          <ChangeMap theme={theme} onTheme={setTheme} />
        </MotionConfig>
      </TooltipProvider>
    </MapContext>
  )
}

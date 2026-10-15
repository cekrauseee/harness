import { cn } from '@/shared/lib/utils'

// Static class names so Tailwind generates them; layers beyond the palette reuse its colours.
const LAYER_BG = ['bg-l0', 'bg-l1', 'bg-l2', 'bg-l3', 'bg-l4', 'bg-l5']

export function LayerDot({ layer, className }: { layer: number; className?: string }) {
  return <i className={cn('inline-block size-1.5 shrink-0 rounded-full', LAYER_BG[layer % LAYER_BG.length], className)} />
}

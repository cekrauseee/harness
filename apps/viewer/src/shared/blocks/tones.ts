import type { MapAttention, MapFile } from '@/data'

type Severity = NonNullable<MapAttention['severity']>
type Status = MapAttention['status']

export type Tone = 'ok' | 'warn' | 'danger' | 'neutral'

export const TONE: Record<Tone, string> = {
  ok: 'bg-ok/12 text-ok',
  warn: 'bg-warn/14 text-warn',
  danger: 'bg-destructive/10 text-destructive',
  neutral: 'bg-secondary text-muted-foreground',
}
export const SEVERITY_TONE: Record<Severity, Tone> = { critical: 'danger', high: 'warn', medium: 'neutral', low: 'neutral' }
export const STATUS_TONE: Record<Status, Tone> = { handled: 'ok', partial: 'warn', open: 'danger', unreported: 'neutral' }
export const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'bg-destructive',
  high: 'bg-warn',
  medium: 'bg-muted-foreground/40',
  low: 'bg-muted-foreground/20',
}
export const STATUS_TEXT: Record<Status, string> = {
  handled: 'text-ok',
  partial: 'text-warn',
  open: 'text-destructive',
  unreported: 'text-muted-foreground',
}
export const FILE_STATUS: Record<MapFile['status'], [label: string, tone: Tone]> = {
  added: ['New file', 'ok'],
  modified: ['New code', 'neutral'],
  deleted: ['Deleted', 'danger'],
  renamed: ['Renamed', 'neutral'],
  copied: ['Copied', 'neutral'],
  'type-changed': ['Type changed', 'neutral'],
}

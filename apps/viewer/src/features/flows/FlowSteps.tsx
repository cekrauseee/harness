import { useEffect, useRef } from 'react'
import { Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { refMeta, refTarget, testMeta, useMap, type MapFlow, type MapStep } from '@/data'
import { CardChips, CodeRef, Disclosure, Prose, Refs, Section } from '@/shared/blocks'
import { Item } from '@/shared/motion'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import { Collapsible, CollapsibleContent } from '@/shared/ui/collapsible'
import { CommandLine } from './CommandLine'

export interface FlowActions {
  onSelectCard: (id: string) => void
  onOpenCode: (path: string, target?: string | null) => void
}

function Technical({ step, flow, onOpenCode, onSelectCard }: { step: MapStep; flow: MapFlow } & FlowActions) {
  const files = useMap().map.files
  const commands = [...(step.url ? [step.url] : []), ...step.commands]
  return (
    <div className="flex min-w-0 flex-col gap-4 pt-3">
      {commands.length > 0 && (
        <div className="grid gap-1.5">
          {commands.map((c) => (
            <CommandLine key={c} text={c} />
          ))}
        </div>
      )}
      {step.code.length > 0 && (
        <Section title="Code that runs">
          <Refs>
            {step.code.map((r, i) => (
              <CodeRef key={i} meta={refMeta(r)} text={r.note ?? files[r.path]?.role} onOpen={() => onOpenCode(r.path, refTarget(r))} />
            ))}
          </Refs>
        </Section>
      )}
      {step.test && (
        <Section title="Proven by">
          <Refs>
            <CodeRef meta={testMeta(step.test)} text={step.test.title} onOpen={() => onOpenCode(step.test!.path, refTarget(step.test!))} />
          </Refs>
        </Section>
      )}
      {flow.test && (
        <Section title="Whole flow automated by">
          <Refs>
            <CodeRef meta={testMeta(flow.test)} text={flow.test.title} onOpen={() => onOpenCode(flow.test!.path, refTarget(flow.test!))} />
          </Refs>
        </Section>
      )}
      {step.cards.length > 0 && (
        <Section title="Cards">
          <CardChips ids={step.cards} onSelect={onSelectCard} />
        </Section>
      )}
    </div>
  )
}

interface Props extends FlowActions {
  flow: MapFlow
  step: number
  onStep: (step: number) => void
  showTech: boolean
  onShowTech: (open: boolean) => void
}

/** Vertical stepper: the current step expanded, technical details on demand, sticky footer navigation. */
export function FlowSteps({ flow, step, onStep, showTech, onShowTech, ...actions }: Props) {
  const n = flow.steps.length
  const items = useRef<(HTMLLIElement | null)[]>([])
  useEffect(() => {
    // once the expand has started
    const t = setTimeout(() => items.current[step]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 220)
    return () => clearTimeout(t)
  }, [step])
  const go = (s: number) => s >= 0 && s < n && onStep(s)

  return (
    <>
      <Item as="ol" className="flex flex-col">
        {flow.steps.map((st, j) => {
          const cur = j === step
          const past = j < step
          const hasTech = st.url || st.commands.length || st.code.length || st.test || st.cards.length || flow.test
          return (
            <Item
              as="li"
              key={j}
              ref={(el: HTMLLIElement | null) => {
                items.current[j] = el
              }}
              className={cn('cm-step relative grid grid-cols-[28px_minmax(0,1fr)] gap-x-3.5', past && 'is-past')}
            >
              <button
                onClick={() => go(j)}
                aria-label={`Go to step ${j + 1}`}
                aria-current={cur ? 'step' : undefined}
                className={cn(
                  'relative z-10 grid size-7 place-items-center rounded-full border bg-background font-mono text-[11px] text-muted-foreground transition-all duration-300 hover:scale-105',
                  past && 'border-transparent bg-brand-soft text-brand',
                  cur && 'border-brand bg-brand text-white shadow-[0_0_0_4px_var(--brand-soft)]',
                )}
              >
                <span
                  className={cn(
                    'col-start-1 row-start-1 transition-all duration-300',
                    past ? 'scale-50 opacity-0' : 'scale-100 opacity-100',
                  )}
                >
                  {j + 1}
                </span>
                <Check
                  className={cn(
                    'col-start-1 row-start-1 size-3.5 transition-all duration-300',
                    past ? 'scale-100 opacity-100' : 'scale-50 opacity-0',
                  )}
                />
              </button>
              <div className="min-w-0 pb-4">
                <button
                  onClick={() => go(j)}
                  tabIndex={cur ? -1 : 0}
                  className={cn(
                    'block w-full pt-1 text-left text-[13px] leading-snug text-muted-foreground transition-colors hover:text-foreground',
                    cur && 'cursor-default text-[14.5px] font-semibold tracking-tight text-foreground',
                  )}
                >
                  {st.title ?? st.do}
                </button>
                <Collapsible open={cur}>
                  <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
                    <div className="flex min-w-0 flex-col gap-2.5 pt-2.5">
                      <span className="cm-eyebrow">{st.actor}</span>
                      {st.title && <Prose>{st.do}</Prose>}
                      <div className="rounded-lg bg-secondary/70 px-3 py-2.5 text-[12.5px] leading-relaxed [overflow-wrap:anywhere]">
                        <span className="mb-0.5 block text-[10.5px] font-medium tracking-[0.08em] text-ok uppercase">Expected</span>
                        {st.expect}
                      </div>
                      {hasTech && (
                        <Disclosure label="Technical details" open={showTech} onOpenChange={onShowTech}>
                          <Technical step={st} flow={flow} {...actions} />
                        </Disclosure>
                      )}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </div>
            </Item>
          )
        })}
      </Item>

      <footer className="sticky bottom-0 -mx-5 -mb-5 flex items-center justify-between gap-2 border-t bg-background/80 px-5 py-3 backdrop-blur-md">
        <Button variant="outline" onClick={() => go(step - 1)} disabled={step === 0}>
          <ChevronLeft />
          Previous
        </Button>
        <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
          {step + 1} / {n}
        </span>
        <Button onClick={() => go(step + 1)} disabled={step === n - 1}>
          Next
          <ChevronRight />
        </Button>
      </footer>
    </>
  )
}

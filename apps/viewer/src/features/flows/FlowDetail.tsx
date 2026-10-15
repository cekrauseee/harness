import { refTarget, testMeta, type MapFlow } from '@/data'
import { CardChips, CodeRef, Header, Prose, Refs, Section } from '@/shared/blocks'
import { FlowSteps, type FlowActions } from './FlowSteps'

interface Props extends FlowActions {
  flow: MapFlow
  step: number
  onStep: (step: number) => void
  showTech: boolean
  onShowTech: (open: boolean) => void
}

/** A flow: its reproduction steps when it has them, otherwise trigger, outcome and path. */
export function FlowDetail({ flow, step, onStep, showTech, onShowTech, ...actions }: Props) {
  const n = flow.steps.length
  return (
    <>
      <Header tag={flow.actor ? `Flow · ${flow.actor}` : 'Flow'} title={flow.title} sub={n ? (flow.outcome ?? flow.trigger) : undefined}>
        {n > 0 && (
          <div
            className="mt-4 h-[3px] overflow-hidden rounded-full bg-border"
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={n}
            aria-valuenow={step + 1}
          >
            <div
              className="h-full origin-left rounded-full bg-brand transition-transform duration-500 ease-out-soft"
              style={{ transform: `scaleX(${(step + 1) / n})` }}
            />
          </div>
        )}
      </Header>
      {n > 0 ? (
        <FlowSteps flow={flow} step={step} onStep={onStep} showTech={showTech} onShowTech={onShowTech} {...actions} />
      ) : (
        <>
          {flow.trigger && (
            <Section title="Trigger">
              <Prose>{flow.trigger}</Prose>
            </Section>
          )}
          {flow.outcome && (
            <Section title="Outcome">
              <Prose>{flow.outcome}</Prose>
            </Section>
          )}
          {flow.test && (
            <Section title="Automated by">
              <Refs>
                <CodeRef
                  meta={testMeta(flow.test)}
                  text={flow.test.title}
                  onOpen={() => actions.onOpenCode(flow.test!.path, refTarget(flow.test!))}
                />
              </Refs>
            </Section>
          )}
          {flow.cards.length > 0 && (
            <Section title="Path">
              <CardChips ids={flow.cards} onSelect={actions.onSelectCard} />
            </Section>
          )}
        </>
      )}
    </>
  )
}

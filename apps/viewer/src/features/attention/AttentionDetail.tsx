import { refMeta, refTarget, testMeta, type MapAttention } from '@/data'
import { CardChips, CodeRef, Header, Prose, Refs, Section, SEVERITY_TONE, STATUS_TONE, Steps, Tag } from '@/shared/blocks'

interface Props {
  point: MapAttention
  onSelectCard: (id: string) => void
  onOpenCode: (path: string, target?: string | null) => void
}

export function AttentionDetail({ point, onSelectCard, onOpenCode }: Props) {
  const meta = [point.proof && `proof: ${point.proof}`, point.owner && `owner: ${point.owner}`].filter(Boolean).join(' · ')
  return (
    <>
      <Header tag={point.category ?? 'Attention'} title={point.title}>
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          {point.severity && <Tag tone={SEVERITY_TONE[point.severity]}>{point.severity}</Tag>}
          <Tag tone={STATUS_TONE[point.status]}>{point.status}</Tag>
          {meta && <span className="ml-1 font-mono text-[10.5px] text-muted-foreground">{meta}</span>}
        </div>
      </Header>
      {point.scenario && (
        <Section title="Scenario">
          <Prose>{point.scenario}</Prose>
        </Section>
      )}
      {point.handling && (
        <Section title="How it is handled">
          <Prose>{point.handling}</Prose>
        </Section>
      )}
      {point.evidence.length > 0 && (
        <Section title="Evidence in code">
          <Refs>
            {point.evidence.map((ev, i) => (
              <CodeRef key={i} meta={refMeta(ev)} text={ev.note} onOpen={() => onOpenCode(ev.path, refTarget(ev))} />
            ))}
          </Refs>
        </Section>
      )}
      {point.tests.length > 0 && (
        <Section title="Proven by tests">
          <Refs>
            {point.tests.map((t, i) => (
              <CodeRef key={i} meta={testMeta(t)} text={t.title} onOpen={() => onOpenCode(t.path, refTarget(t))} />
            ))}
          </Refs>
        </Section>
      )}
      {point.qa.length > 0 && (
        <Section title="Manual checks">
          <Steps items={point.qa} />
        </Section>
      )}
      {point.residual && (
        <Section title="Residual risk">
          <Prose muted>{point.residual}</Prose>
        </Section>
      )}
      {point.cards.length > 0 && (
        <Section title="Cards">
          <CardChips ids={point.cards} onSelect={onSelectCard} />
        </Section>
      )}
    </>
  )
}

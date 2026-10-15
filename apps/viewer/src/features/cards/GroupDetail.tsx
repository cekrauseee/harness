import type { MapCard, MapGroup } from '@/data'
import { CardChips, Header, Section } from '@/shared/blocks'

export function GroupDetail({ group, cards, onSelectCard }: { group: MapGroup; cards: MapCard[]; onSelectCard: (id: string) => void }) {
  return (
    <>
      <Header tag="Module" title={group.title} sub={group.summary} />
      <Section title={`Cards · ${cards.length}`}>
        <CardChips ids={cards.map((c) => c.id)} onSelect={onSelectCard} />
      </Section>
    </>
  )
}

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import fixture from '../../fixtures/synthetic/map.json'
import { MapContext, indexMap, type HarnessMap } from '@/data'
import { TooltipProvider } from '@/shared/ui/tooltip'
import { ChangeMap } from './ChangeMap'

function renderMap() {
  const index = indexMap(fixture as unknown as HarnessMap)
  const result = render(
    <MapContext value={index}>
      <TooltipProvider>
        <ChangeMap theme="system" onTheme={() => {}} />
      </TooltipProvider>
    </MapContext>,
  )
  const sheet = () => within(screen.getByRole('complementary', { name: 'Details' }))
  const card = (id: string) => result.container.querySelector<HTMLElement>(`[data-node="${id}"]`)!
  return { user: userEvent.setup(), sheet, card, container: result.container }
}

describe('change map', () => {
  it('opens a card from the canvas and returns to the index', async () => {
    const { user, sheet, card, container } = renderMap()
    // the authored edge is drawn apart from import edges, with its label
    expect(container.querySelectorAll('.cm-edge.authored')).toHaveLength(1)
    expect(screen.getByText('posts the invitation')).toBeInTheDocument()
    await user.click(card('invites'))
    expect(sheet().getByRole('heading', { level: 2, name: 'Invitations' })).toBeInTheDocument()
    expect(card('invites')).toHaveAttribute('aria-pressed', 'true')
    await user.click(sheet().getByRole('button', { name: 'Back' }))
    expect(await sheet().findByRole('heading', { level: 1, name: 'Shared reading lists' })).toBeInTheDocument()
  })

  it('jumps to an attention point from search and clears it with Escape', async () => {
    const { user, sheet } = renderMap()
    await user.keyboard('{Meta>}k{/Meta}')
    await user.type(screen.getByPlaceholderText(/Search cards/), 'invite token')
    await user.click(await screen.findByRole('option', { name: /An invite token opens exactly one list/ }))
    expect(await sheet().findByRole('heading', { level: 2, name: 'An invite token opens exactly one list' })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(sheet().queryByRole('heading', { level: 2 })).not.toBeInTheDocument())
  })

  it('steps through a flow with buttons and arrow keys', async () => {
    const { user, sheet } = renderMap()
    await user.click(sheet().getByRole('button', { name: /Invite a reader/ }))
    const current = () => sheet().getByRole('button', { current: 'step' })
    expect(current()).toHaveAccessibleName('Go to step 1')
    await user.click(sheet().getByRole('button', { name: /Next/ }))
    expect(current()).toHaveAccessibleName('Go to step 2')
    await user.keyboard('{ArrowRight}')
    expect(current()).toHaveAccessibleName('Go to step 3')
    await user.keyboard('{ArrowLeft}')
    expect(current()).toHaveAccessibleName('Go to step 2')
  })

  it('opens a file in the code panel and closes it', async () => {
    const { user, sheet, card } = renderMap()
    await user.click(card('invites'))
    await user.click(sheet().getByRole('button', { name: /invites\.ts/ }))
    const panel = await screen.findByRole('complementary', { name: 'Code' })
    expect(within(panel).getByText('invites.ts')).toBeInTheDocument()
    await waitFor(() => expect(panel).toHaveTextContent('const TTL_MS = 7 * 24 * 60 * 60 * 1000'))
    await user.click(within(panel).getByRole('button', { name: 'Close code' }))
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Code' })).not.toBeInTheDocument())
  })
})

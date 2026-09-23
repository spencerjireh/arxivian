import { screen, fireEvent, within } from '@testing-library/react'
import FeedCard from '@/features/feed/components/FeedCard'
import { renderWithProviders } from '../../../../helpers/renderWithProviders'
import { makeFeedItem } from '../../../../fixtures/feed'
import type { FeedItem } from '@/types/api'

vi.mock('framer-motion', () => import('../../../../mocks/framer-motion'))

function renderCard(
  item: FeedItem = makeFeedItem(),
  {
    signedIn = true,
    onImplementing,
    onShip,
  }: {
    signedIn?: boolean
    onImplementing?: (arxivId: string) => void
    onShip?: (arxivId: string, repoUrl: string) => void
  } = {}
) {
  const onSave = vi.fn()
  const onDismiss = vi.fn()
  renderWithProviders(
    <FeedCard
      item={item}
      signedIn={signedIn}
      onSave={onSave}
      onDismiss={onDismiss}
      onImplementing={onImplementing}
      onShip={onShip}
    />
  )
  return { onSave, onDismiss }
}

const implementing = {
  state: 'implementing' as const,
  repo_url: null,
  dismissal_reason: null,
  updated_at: 'x',
}

describe('FeedCard', () => {
  it('links the title to the paper detail route and shows the headline and meta line', () => {
    renderCard()
    const link = screen.getByRole('link', { name: 'Attention Is All You Need' })
    expect(link).toHaveAttribute('href', '/papers/2401.00001')
    expect(screen.getByText('Transformer for machine translation')).toBeInTheDocument()
    expect(
      screen.getByText('one datacenter GPU · public data · pseudocode given')
    ).toBeInTheDocument()
    expect(screen.getByText(/Vaswani, Shazeer, Parmar \+1 more/)).toBeInTheDocument()
  })

  it('draws four meters from the sub-scores with no composite number or band word', () => {
    renderCard()
    const meter = screen.getByRole('list', { name: 'Implementability meter' })
    const values = within(meter)
      .getAllByRole('meter')
      .map((m) => [m.getAttribute('data-dimension'), m.getAttribute('aria-valuenow')])
    expect(values).toEqual([
      ['method_clarity', '80'],
      ['resource_feasibility', '50'],
      ['data_availability', '100'],
      ['demand', '85'],
    ])
    expect(screen.queryByText('71')).not.toBeInTheDocument()
    expect(screen.queryByText(/HIGH|Strong/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/Low confidence/)).not.toBeInTheDocument()
  })

  it('renders a hollow "not available" segment for a null sub-score, never a low fill', () => {
    renderCard(makeFeedItem({ scores: { ...makeFeedItem().scores!, demand: null } }))
    const meter = screen.getByRole('list', { name: 'Implementability meter' })
    expect(within(meter).getAllByRole('meter')).toHaveLength(3)
    const hollow = within(meter).getByRole('img', { name: 'Demand not available' })
    expect(hollow).toHaveAttribute('data-value', 'null')
  })

  it('appends the compute-fit chip only when the profile matches', () => {
    renderCard(makeFeedItem({ compute_match: true }))
    expect(screen.getByText('Fits your compute')).toBeInTheDocument()
  })

  it('offers Save and Dismiss only, and no Implementing button, on the feed', () => {
    const { onSave, onDismiss } = renderCard()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(onSave).toHaveBeenCalledWith('2401.00001')
    expect(onDismiss).toHaveBeenCalledWith('2401.00001')
    expect(screen.queryByRole('button', { name: 'Mark as Implementing' })).not.toBeInTheDocument()
  })

  it('shows an implementing paper as a chip on the feed instead of an unpressed Save', () => {
    const { onSave } = renderCard(makeFeedItem({ state: implementing }))
    expect(screen.getByText('Implementing')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Save/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('offers Implementing where the handler is given (detail and Library)', () => {
    const onImplementing = vi.fn()
    renderCard(makeFeedItem(), { onImplementing })
    fireEvent.click(screen.getByRole('button', { name: 'Mark as Implementing' }))
    expect(onImplementing).toHaveBeenCalledWith('2401.00001')
  })

  it('shows an anonymous reader a Save that goes to sign-in and no Dismiss', () => {
    renderCard(makeFeedItem(), { signedIn: false })
    expect(screen.getByRole('link', { name: 'Save' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
  })

  it('reflects the saved state', () => {
    renderCard(
      makeFeedItem({
        state: { state: 'saved', repo_url: null, dismissal_reason: null, updated_at: 'x' },
      })
    )
    expect(screen.getByRole('button', { name: 'Saved' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows a shipped chip with the repo link instead of actions', () => {
    renderCard(
      makeFeedItem({
        state: {
          state: 'shipped',
          repo_url: 'https://github.com/x/y',
          dismissal_reason: null,
          updated_at: 'x',
        },
      })
    )
    expect(screen.getByText('Shipped')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Repo/ })).toHaveAttribute(
      'href',
      'https://github.com/x/y'
    )
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
  })

  it('renders an unscored card with the paper and actions only', () => {
    renderCard(makeFeedItem({ scores: null, headline: null, meta: [], scored_at: null }))
    expect(screen.getByRole('link', { name: 'Attention Is All You Need' })).toBeInTheDocument()
    expect(screen.getByText('Not scored yet')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Implementability meter' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
  })

  it('offers "Mark as shipped" only for an implementing paper when onShip is given', () => {
    renderCard(makeFeedItem({ state: implementing }), { onImplementing: vi.fn() })
    expect(screen.queryByRole('button', { name: 'Mark as shipped' })).not.toBeInTheDocument()
  })

  it('asks for the repo url and calls onShip with it', () => {
    const onShip = vi.fn()
    renderCard(makeFeedItem({ state: implementing }), { onImplementing: vi.fn(), onShip })

    fireEvent.click(screen.getByRole('button', { name: 'Mark as shipped' }))
    const input = screen.getByLabelText('Repository URL')
    fireEvent.change(input, { target: { value: '  https://github.com/x/y  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))

    expect(onShip).toHaveBeenCalledWith('2401.00001', 'https://github.com/x/y')
    expect(screen.queryByLabelText('Repository URL')).not.toBeInTheDocument()
  })

  it('cancel closes the repo form without shipping', () => {
    const onShip = vi.fn()
    renderCard(makeFeedItem({ state: implementing }), { onImplementing: vi.fn(), onShip })
    fireEvent.click(screen.getByRole('button', { name: 'Mark as shipped' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Repository URL')).not.toBeInTheDocument()
    expect(onShip).not.toHaveBeenCalled()
  })
})

import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import FeedCard from '../../../../src/components/feed/FeedCard'
import { makeFeedItem } from '../../../fixtures/feed'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

function renderCard(item = makeFeedItem(), pendingAction = null) {
  const onSave = vi.fn()
  const onDismiss = vi.fn()
  const onImplementing = vi.fn()
  renderWithProviders(
    <FeedCard
      item={item}
      onSave={onSave}
      onDismiss={onDismiss}
      onImplementing={onImplementing}
      pendingAction={pendingAction}
    />
  )
  return { onSave, onDismiss, onImplementing }
}

describe('FeedCard', () => {
  it('links the title to the paper detail route and shows the verdict', () => {
    renderCard()
    const link = screen.getByRole('link', { name: 'Attention Is All You Need' })
    expect(link).toHaveAttribute('href', '/papers/2401.00001')
    expect(screen.getByText(/Transformer for machine translation/)).toBeInTheDocument()
    expect(screen.getByText(/Vaswani, Shazeer, Parmar \+1 more/)).toBeInTheDocument()
  })

  it('renders only truthy signal chips and never a negative code chip', () => {
    renderCard()
    expect(screen.getByText('Pseudocode present')).toBeInTheDocument()
    expect(screen.getByText('Public datasets')).toBeInTheDocument()
    expect(screen.getByText('1 GPU')).toBeInTheDocument()
    expect(screen.queryByText('Code released')).not.toBeInTheDocument()
    expect(screen.queryByText(/no code/i)).not.toBeInTheDocument()
  })

  it('shows the composite badge with its band', () => {
    renderCard()
    const badge = screen.getByLabelText('Score 71 of 100, high')
    expect(badge).toHaveAttribute('data-band', 'HIGH')
  })

  it('marks low confidence', () => {
    renderCard(makeFeedItem({ low_confidence: ['method_clarity'] }))
    expect(screen.getByLabelText('Low confidence: Method clarity')).toBeInTheDocument()
  })

  it('fires actions with the arXiv id', () => {
    const { onSave, onDismiss, onImplementing } = renderCard()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    fireEvent.click(screen.getByRole('button', { name: 'Mark as Implementing' }))
    expect(onSave).toHaveBeenCalledWith('2401.00001')
    expect(onDismiss).toHaveBeenCalledWith('2401.00001')
    expect(onImplementing).toHaveBeenCalledWith('2401.00001')
  })

  it('reflects saved and shipped states', () => {
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
})

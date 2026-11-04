import { screen, fireEvent, within } from '@testing-library/react'
import FeedPost from '@/features/feed/components/FeedPost'
import { makeFeedItem } from '../../../../fixtures/feed'
import { renderWithProviders } from '../../../../helpers/renderWithProviders'
import { lifecycle, resetLifecycle, usePaperLifecycle } from '../../../../mocks/lifecycle'
import type { FeedItem } from '@/types/api'

vi.mock('framer-motion', () => import('../../../../mocks/framer-motion'))

vi.mock('@/features/paper/hooks/usePaperLifecycle', () => import('../../../../mocks/lifecycle'))

function renderPost(
  item: FeedItem = makeFeedItem(),
  { signedIn = true, offerImplementing = false, defaultExpanded = false } = {}
) {
  renderWithProviders(
    <FeedPost
      item={item}
      signedIn={signedIn}
      offerImplementing={offerImplementing}
      defaultExpanded={defaultExpanded}
    />
  )
}

function expand() {
  fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
}

const implementing = {
  state: 'implementing' as const,
  repo_url: null,
  dismissal_reason: null,
  updated_at: 'x',
}

beforeEach(() => {
  resetLifecycle()
})

describe('FeedPost', () => {
  it('shows the category, date, title link and a clamped abstract when collapsed', () => {
    renderPost()
    expect(screen.getByText('cs.CL')).toBeInTheDocument()
    expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Attention Is All You Need' })).toHaveAttribute(
      'href',
      '/papers/2401.00001'
    )
    const abstract = screen.getByText(/We propose a new simple network architecture/)
    expect(abstract).toHaveClass('line-clamp-2')
    expect(screen.queryByText(/Vaswani/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /PDF/ })).not.toBeInTheDocument()
    expect(usePaperLifecycle).not.toHaveBeenCalled()
  })

  it('draws the two feed meters with no data gate, composite number or band word', () => {
    renderPost()
    const meter = screen.getByRole('list', { name: 'Implementability meter' })
    const values = within(meter)
      .getAllByRole('meter')
      .map((m) => [m.getAttribute('data-dimension'), m.getAttribute('aria-valuenow')])
    expect(values).toEqual([
      ['method_clarity', '80'],
      ['resource_feasibility', '50'],
    ])
    expect(screen.queryByText('Data')).not.toBeInTheDocument()
    expect(screen.queryByText('71')).not.toBeInTheDocument()
    expect(screen.queryByText(/HIGH|Strong/)).not.toBeInTheDocument()
  })

  it('hatches a low-confidence dimension instead of hiding it', () => {
    renderPost(makeFeedItem({ low_confidence: ['method_clarity'] }))
    const low = screen.getByRole('meter', { name: 'Method 80 of 100 (low confidence)' })
    expect(low.firstElementChild).toHaveClass('meter-hatched')
    expect(screen.getByRole('meter', { name: 'Compute 50 of 100' })).toBeInTheDocument()
  })

  it('renders a hollow "not available" segment for a null sub-score, never a low fill', () => {
    renderPost(makeFeedItem({ scores: { ...makeFeedItem().scores!, resource_feasibility: null } }))
    const hollow = screen.getByRole('img', { name: 'Compute not available' })
    expect(hollow).toHaveAttribute('data-value', 'null')
  })

  it('shows the compute tier chip from the level and nothing for an unknown tier', () => {
    renderPost(makeFeedItem({ compute_tier: 4 }))
    expect(screen.getByText('Laptop / CPU')).toBeInTheDocument()
    renderPost(
      makeFeedItem({ compute_tier: null, paper: { ...makeFeedItem().paper, arxiv_id: 'b' } })
    )
    expect(screen.queryByText('Datacenter GPU')).not.toBeInTheDocument()
  })

  it('shows a Code chip only for a released codebase, never a negative claim', () => {
    renderPost(makeFeedItem({ code_released: true }))
    expect(screen.getByText('Code')).toBeInTheDocument()
    renderPost(
      makeFeedItem({ code_released: false, paper: { ...makeFeedItem().paper, arxiv_id: 'b' } })
    )
    renderPost(
      makeFeedItem({ code_released: null, paper: { ...makeFeedItem().paper, arxiv_id: 'c' } })
    )
    expect(screen.getAllByText('Code')).toHaveLength(1)
    expect(screen.queryByText(/no code/i)).not.toBeInTheDocument()
  })

  it('appends the compute-fit and keyword chips only when they apply', () => {
    renderPost(makeFeedItem({ compute_match: true, keyword_match: true }))
    expect(screen.getByText('Fits your compute')).toBeInTheDocument()
    expect(screen.getByText('Keyword match')).toBeInTheDocument()
  })

  it('expands from the chevron to reveal the abstract, authors, actions and links', () => {
    renderPost()
    const chevron = screen.getByRole('button', { name: 'Expand' })
    expect(chevron).toHaveAttribute('aria-expanded', 'false')
    expand()
    const collapse = screen.getByRole('button', { name: 'Collapse' })
    expect(collapse).toHaveAttribute('aria-expanded', 'true')
    expect(document.getElementById(collapse.getAttribute('aria-controls')!)).toBeInTheDocument()
    expect(screen.getByText(/We propose a new simple network architecture/)).not.toHaveClass(
      'line-clamp-2'
    )
    expect(screen.getByText(/Vaswani, Shazeer, Parmar \+1 more/)).toBeInTheDocument()
    expect(usePaperLifecycle).toHaveBeenCalledWith('2401.00001', null)
    expect(screen.getByRole('link', { name: /PDF/ })).toHaveAttribute(
      'href',
      'https://arxiv.org/pdf/2401.00001'
    )
    expect(screen.getByRole('link', { name: /arXiv/ })).toHaveAttribute(
      'href',
      'https://arxiv.org/abs/2401.00001'
    )
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(lifecycle.save).toHaveBeenCalledTimes(1)
    expect(lifecycle.dismiss).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Mark as Implementing' })).not.toBeInTheDocument()
    // Clicking an action does not collapse the post.
    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument()
  })

  it('toggles on a click in the body but not on the title link', () => {
    renderPost()
    fireEvent.click(screen.getByText(/We propose a new simple network architecture/))
    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Attention Is All You Need' }))
    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Jan 15, 2024/))
    expect(screen.getByRole('button', { name: 'Expand' })).toBeInTheDocument()
  })

  it('does not toggle while text is being selected', () => {
    const getSelection = vi
      .spyOn(window, 'getSelection')
      .mockReturnValue({ isCollapsed: false } as Selection)
    renderPost()
    fireEvent.click(screen.getByText(/We propose a new simple network architecture/))
    expect(screen.getByRole('button', { name: 'Expand' })).toBeInTheDocument()
    getSelection.mockRestore()
  })

  it('opens by default where asked (Library)', () => {
    renderPost(makeFeedItem(), { defaultExpanded: true })
    expect(screen.getByRole('button', { name: 'Collapse' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
  })

  it('shows an implementing paper as a chip on the feed instead of an unpressed Save', () => {
    renderPost(makeFeedItem({ state: implementing }))
    expand()
    expect(screen.getByText('Implementing')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Save/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dismiss' })).toBeInTheDocument()
  })

  it('offers Implementing where the list allows it (Library)', () => {
    renderPost(makeFeedItem(), { offerImplementing: true, defaultExpanded: true })
    fireEvent.click(screen.getByRole('button', { name: 'Mark as Implementing' }))
    expect(lifecycle.toggleImplementing).toHaveBeenCalledTimes(1)
  })

  it('shows an anonymous reader a Save that goes to sign-in and no Dismiss', () => {
    renderPost(makeFeedItem(), { signedIn: false })
    expand()
    expect(screen.getByRole('link', { name: 'Save' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    expect(usePaperLifecycle).not.toHaveBeenCalled()
  })

  it('reflects the saved state', () => {
    renderPost(
      makeFeedItem({
        state: { state: 'saved', repo_url: null, dismissal_reason: null, updated_at: 'x' },
      }),
      { defaultExpanded: true }
    )
    expect(screen.getByRole('button', { name: 'Saved' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows a shipped chip with the repo link instead of actions', () => {
    renderPost(
      makeFeedItem({
        state: {
          state: 'shipped',
          repo_url: 'https://github.com/x/y',
          dismissal_reason: null,
          updated_at: 'x',
        },
      }),
      { defaultExpanded: true }
    )
    expect(screen.getByText('Shipped')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Repo/ })).toHaveAttribute(
      'href',
      'https://github.com/x/y'
    )
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
  })

  it('renders an unscored post with the paper and actions only', () => {
    renderPost(makeFeedItem({ scores: null, headline: null, meta: [], scored_at: null }), {
      defaultExpanded: true,
    })
    expect(screen.getByText('Not scored yet')).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Implementability meter' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
  })

  it('asks for the repo url and ships with it trimmed, and cancel closes the form', () => {
    renderPost(makeFeedItem({ state: implementing }), {
      offerImplementing: true,
      defaultExpanded: true,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Mark as shipped' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByLabelText('Repository URL')).not.toBeInTheDocument()
    expect(lifecycle.ship).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Mark as shipped' }))
    const input = screen.getByLabelText('Repository URL')
    fireEvent.change(input, { target: { value: '  https://github.com/x/y  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(lifecycle.ship).toHaveBeenCalledWith('https://github.com/x/y')
    expect(screen.queryByLabelText('Repository URL')).not.toBeInTheDocument()
  })

  it('spins the button whose transition is in flight', () => {
    usePaperLifecycle.mockReturnValueOnce({ ...lifecycle, pending: 'dismissed' })
    renderPost(makeFeedItem(), { defaultExpanded: true })
    expect(screen.getByRole('button', { name: 'Dismiss' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Save' })).not.toBeDisabled()
  })
})

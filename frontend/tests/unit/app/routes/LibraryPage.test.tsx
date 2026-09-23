import { screen, fireEvent, within } from '@testing-library/react'
import LibraryPage from '@/app/routes/LibraryPage'
import { makeFeedItem, makeLibraryResponse } from '../../../fixtures/feed'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { lifecycle, resetLifecycle, usePaperLifecycle } from '../../../mocks/lifecycle'
import type { FeedItem, PaperLifecycleState } from '@/types/api'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

const mockUseLibrary = vi.fn()
vi.mock('@/features/paper/api/get-library', () => ({
  useLibrary: () => mockUseLibrary(),
}))

vi.mock('@/features/paper/hooks/usePaperLifecycle', () => import('../../../mocks/lifecycle'))

function item(arxivId: string, title: string, state: PaperLifecycleState): FeedItem {
  return makeFeedItem({
    paper: { ...makeFeedItem().paper, arxiv_id: arxivId, title },
    state: {
      state,
      repo_url: state === 'shipped' ? 'https://github.com/x/y' : null,
      dismissal_reason: null,
      updated_at: 'x',
    },
  })
}

function ready(overrides = {}) {
  return { data: makeLibraryResponse(overrides), isLoading: false, error: null }
}

beforeEach(() => {
  resetLifecycle()
})

describe('LibraryPage', () => {
  it('shows a spinner while loading', () => {
    mockUseLibrary.mockReturnValue({ data: undefined, isLoading: true, error: null })
    renderWithProviders(<LibraryPage />)
    expect(screen.getByText('Library')).toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('shows the error message', () => {
    mockUseLibrary.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    })
    renderWithProviders(<LibraryPage />)
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows one empty state with a link to the feed when every group is empty', () => {
    mockUseLibrary.mockReturnValue(ready())
    renderWithProviders(<LibraryPage />)
    expect(screen.getByText('Nothing saved yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'feed' })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('heading', { name: 'Saved' })).not.toBeInTheDocument()
  })

  it('renders the non-empty groups in lifecycle order with counts', () => {
    mockUseLibrary.mockReturnValue(
      ready({
        saved: [item('a', 'Saved one', 'saved'), item('b', 'Saved two', 'saved')],
        shipped: [item('c', 'Shipped one', 'shipped')],
      })
    )
    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('3 papers')).toBeInTheDocument()
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(headings).toEqual(['Saved', 'Shipped'])

    const saved = screen.getByRole('region', { name: 'Saved' })
    expect(within(saved).getByText('2')).toBeInTheDocument()
    expect(within(saved).getByRole('link', { name: 'Saved one' })).toBeInTheDocument()

    const shipped = screen.getByRole('region', { name: 'Shipped' })
    expect(within(shipped).getByRole('link', { name: /Repo/ })).toHaveAttribute(
      'href',
      'https://github.com/x/y'
    )
  })

  it('offers Implementing and Ship on every card and ships with the entered repo url', () => {
    mockUseLibrary.mockReturnValue(
      ready({ implementing: [item('a', 'Building it', 'implementing')] })
    )
    renderWithProviders(<LibraryPage />)
    expect(usePaperLifecycle).toHaveBeenCalledWith(
      'a',
      expect.objectContaining({ state: 'implementing' })
    )
    expect(screen.getByRole('button', { name: 'Implementing' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )

    fireEvent.click(screen.getByRole('button', { name: 'Mark as shipped' }))
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/me/repo' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(lifecycle.ship).toHaveBeenCalledWith('https://github.com/me/repo')
  })

  it('save and dismiss go to the card lifecycle', () => {
    mockUseLibrary.mockReturnValue(ready({ saved: [item('a', 'Saved one', 'saved')] }))
    renderWithProviders(<LibraryPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Saved' }))
    expect(lifecycle.save).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(lifecycle.dismiss).toHaveBeenCalledTimes(1)
  })
})

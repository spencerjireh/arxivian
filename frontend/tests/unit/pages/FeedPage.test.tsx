import { screen, fireEvent } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import FeedPage from '../../../src/pages/FeedPage'
import { useUserStore } from '../../../src/stores/userStore'
import { makeFeedItem, makeFeedResponse } from '../../fixtures/feed'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

const mockUseInfiniteFeed = vi.fn()
const setMutateAsync = vi.fn().mockResolvedValue({})
const clearMutateAsync = vi.fn().mockResolvedValue(undefined)

vi.mock('../../../src/api/feed', () => ({
  useInfiniteFeed: (params: unknown) => mockUseInfiniteFeed(params),
}))
vi.mock('../../../src/api/paperState', () => ({
  useSetPaperState: () => ({ mutateAsync: setMutateAsync }),
  useClearPaperState: () => ({ mutateAsync: clearMutateAsync }),
}))

function feedState(overrides: Record<string, unknown>) {
  return {
    data: undefined,
    isLoading: false,
    isPlaceholderData: false,
    error: null,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    ...overrides,
  }
}

beforeEach(() => {
  setMutateAsync.mockClear()
  clearMutateAsync.mockClear()
})

describe('FeedPage', () => {
  it('shows a spinner while loading', () => {
    mockUseInfiniteFeed.mockReturnValue(feedState({ isLoading: true }))
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    expect(screen.getByText('Feed')).toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('shows the error message', () => {
    mockUseInfiniteFeed.mockReturnValue(feedState({ error: new Error('Network error') }))
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows the empty state', () => {
    mockUseInfiniteFeed.mockReturnValue(
      feedState({ data: { pages: [makeFeedResponse([])], pageParams: [0] } }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    expect(screen.getByText('No papers scored for this week yet')).toBeInTheDocument()
  })

  it('renders cards, the week label and passes URL params to the hook', () => {
    mockUseInfiniteFeed.mockReturnValue(
      feedState({ data: { pages: [makeFeedResponse([makeFeedItem()])], pageParams: [0] } }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed?week=2026-08-03&min_score=40&category=cs.LG'] })
    expect(screen.getByText('Week of Aug 3')).toBeInTheDocument()
    expect(screen.getByText('1 paper')).toBeInTheDocument()
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    expect(mockUseInfiniteFeed).toHaveBeenCalledWith({ week: '2026-08-03', min_score: 40, category: 'cs.LG' })
  })

  it('dismiss and save call the mutation with the arXiv id', () => {
    mockUseInfiniteFeed.mockReturnValue(
      feedState({ data: { pages: [makeFeedResponse([makeFeedItem()])], pageParams: [0] } }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(setMutateAsync).toHaveBeenCalledWith({ arxivId: '2401.00001', body: { state: 'dismissed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(setMutateAsync).toHaveBeenCalledWith({ arxivId: '2401.00001', body: { state: 'saved' } })
  })

  it('save on a saved paper clears the state', () => {
    const saved = makeFeedItem({ state: { state: 'saved', repo_url: null, dismissal_reason: null, updated_at: 'x' } })
    mockUseInfiniteFeed.mockReturnValue(
      feedState({ data: { pages: [makeFeedResponse([saved])], pageParams: [0] } }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    fireEvent.click(screen.getByRole('button', { name: 'Saved' }))
    expect(clearMutateAsync).toHaveBeenCalledWith({ arxivId: '2401.00001' })
  })

  it('load more fetches the next page', () => {
    const fetchNextPage = vi.fn()
    mockUseInfiniteFeed.mockReturnValue(
      feedState({
        data: { pages: [makeFeedResponse([makeFeedItem()], { total: 5 })], pageParams: [0] },
        hasNextPage: true,
        fetchNextPage,
      }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    fireEvent.click(screen.getByRole('button', { name: 'Load more' }))
    expect(fetchNextPage).toHaveBeenCalled()
  })

  it('week selector and filters write to the URL', () => {
    mockUseInfiniteFeed.mockReturnValue(
      feedState({
        data: {
          pages: [
            makeFeedResponse([makeFeedItem()], {
              available_weeks: [
                { week_start: '2026-08-03', paper_count: 1 },
                { week_start: '2026-07-27', paper_count: 4 },
              ],
            }),
          ],
          pageParams: [0],
        },
      }),
    )
    function LocationProbe() {
      const { search } = useLocation()
      return <div data-testid="search">{search}</div>
    }
    renderWithProviders(
      <Routes>
        <Route path="/feed" element={<><FeedPage /><LocationProbe /></>} />
      </Routes>,
      { initialEntries: ['/feed'] },
    )
    fireEvent.change(screen.getByLabelText('Digest week'), { target: { value: '2026-07-27' } })
    expect(screen.getByTestId('search').textContent).toBe('?week=2026-07-27')
    fireEvent.click(screen.getByRole('button', { name: '70+' }))
    expect(screen.getByTestId('search').textContent).toBe('?week=2026-07-27&min_score=70')
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'cs.LG' } })
    expect(screen.getByTestId('search').textContent).toBe('?week=2026-07-27&min_score=70&category=cs.LG')
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByTestId('search').textContent).toBe('?week=2026-07-27')
  })

  it('merges profile categories into the category options', () => {
    useUserStore.setState({
      me: {
        id: 'u', email: null, first_name: null, last_name: null, tier: 'free',
        daily_chat_limit: null, chats_used_today: 0,
        preferences: { feed_profile: { categories: ['stat.ML'], compute_profile: 'laptop', keywords: [] } },
      },
    })
    mockUseInfiniteFeed.mockReturnValue(
      feedState({ data: { pages: [makeFeedResponse([makeFeedItem()])], pageParams: [0] } }),
    )
    renderWithProviders(<FeedPage />, { initialEntries: ['/feed'] })
    const options = screen.getAllByRole('option').map((o) => o.textContent)
    expect(options).toContain('stat.ML')
    expect(options).toContain('cs.LG')
    useUserStore.setState({ me: null })
  })
})

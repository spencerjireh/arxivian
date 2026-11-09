import { screen, fireEvent, within, act } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router-dom'
import FeedPage from '@/app/routes/FeedPage'
import { ONBOARDING_PROMPT_KEY } from '@/features/feed/components/OnboardingPrompt'
import { makeFeedItem, makeFeedResponse } from '../../../fixtures/feed'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { lifecycle, resetLifecycle, usePaperLifecycle } from '../../../mocks/lifecycle'
import { makeMe, mockSession, resetSession } from '../../../mocks/auth'
import type { FeedItem, FeedResponse } from '@/types/api'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))
vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

const mockUseFeedWeek = vi.fn()
vi.mock('@/features/feed/api/get-feed', () => ({
  useFeedWeek: (params: unknown) => mockUseFeedWeek(params),
}))

vi.mock('@/features/paper/hooks/usePaperLifecycle', () => import('../../../mocks/lifecycle'))

function feedState(overrides: Record<string, unknown>) {
  return { data: undefined, isLoading: false, isPlaceholderData: false, error: null, ...overrides }
}

function week(items: FeedItem[], overrides: Partial<FeedResponse> = {}) {
  return feedState({ data: makeFeedResponse(items, overrides) })
}

/** A second paper: cs.LG only, laptop tier, code released, published two days later. */
const second = makeFeedItem({
  paper: {
    ...makeFeedItem().paper,
    arxiv_id: '2401.00002',
    title: 'Sparse Mixtures',
    categories: ['cs.LG'],
    published_date: '2024-01-17T00:00:00Z',
  },
  compute_tier: 4,
  code_released: true,
})

const twoWeeks = {
  available_weeks: [
    { week_start: '2026-08-03', paper_count: 2 },
    { week_start: '2026-07-27', paper_count: 4 },
  ],
}

function LocationProbe() {
  const { search } = useLocation()
  return <div data-testid="search">{search}</div>
}

function renderPage(initialEntry = '/') {
  return renderWithProviders(
    <Routes>
      <Route
        path="/"
        element={
          <>
            <FeedPage />
            <LocationProbe />
          </>
        }
      />
    </Routes>,
    { initialEntries: [initialEntry] }
  )
}

function titles(): string[] {
  return screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent ?? '')
}

function openFilters() {
  fireEvent.click(screen.getByRole('button', { name: /^Filters/ }))
  return screen.getByRole('dialog', { name: 'Filters' })
}

let scrollTo: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  resetSession()
  mockSession.isSignedIn = true
  resetLifecycle()
  scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
})

afterEach(() => {
  localStorage.removeItem(ONBOARDING_PROMPT_KEY)
  scrollTo.mockRestore()
})

describe('FeedPage', () => {
  it('shows the masthead and a spinner while loading, with no toolbar yet', () => {
    mockUseFeedWeek.mockReturnValue(feedState({ isLoading: true }))
    renderPage()
    expect(screen.getByRole('heading', { level: 1, name: 'Weekly issue' })).toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument()
  })

  it('reads as one issue to an anonymous reader: no dismissed toggle, Save goes to sign-in', () => {
    mockSession.isSignedIn = false
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()]))
    renderPage('/?dismissed=1&min_score=40')
    expect(screen.getByRole('heading', { level: 1, name: 'Week of Aug 3' })).toBeInTheDocument()
    expect(mockUseFeedWeek).toHaveBeenLastCalledWith({})
    expect(within(openFilters()).queryByLabelText('Show dismissed')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
    expect(screen.getByRole('link', { name: 'Save' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    expect(usePaperLifecycle).not.toHaveBeenCalled()
  })

  it('prompts a signed-in reader without a profile until dismissed', () => {
    mockSession.me = makeMe({ onboarded: false })
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()]))
    renderPage()
    const prompt = screen.getByRole('complementary', { name: 'Set up your feed' })
    expect(within(prompt).getByRole('link', { name: 'Set up' })).toHaveAttribute(
      'href',
      '/onboarding'
    )
    fireEvent.click(within(prompt).getByRole('button', { name: 'Dismiss' }))
    expect(
      screen.queryByRole('complementary', { name: 'Set up your feed' })
    ).not.toBeInTheDocument()
  })

  it('shows the error message', () => {
    mockUseFeedWeek.mockReturnValue(feedState({ error: new Error('Network error') }))
    renderPage()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows the empty week', () => {
    mockUseFeedWeek.mockReturnValue(week([]))
    renderPage()
    expect(screen.getByText('No papers scored for this week yet')).toBeInTheDocument()
  })

  it('sends only the server params to the hook and counts the week', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()]))
    renderPage('/?week=2026-08-03&dismissed=1&category=cs.CL')
    expect(mockUseFeedWeek).toHaveBeenLastCalledWith({
      week: '2026-08-03',
      include_dismissed: true,
    })
    expect(screen.getByText('1 paper')).toBeInTheDocument()
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Filters 2' })).toBeInTheDocument()
  })

  it('admits when the week beat the request cap', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second], { total: 576 }))
    renderPage()
    expect(screen.getByText('top 2 of 576 papers')).toBeInTheDocument()
  })

  it('searches the loaded week from the URL and shows the narrowed count', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second]))
    renderPage('/?q=sparse')
    expect(screen.getByText('1 of 2 papers')).toBeInTheDocument()
    expect(titles()).toEqual(['Sparse Mixtures'])
    expect(screen.getByRole('searchbox')).toHaveValue('sparse')
  })

  it('orders by date under Newest', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second]))
    renderPage('/?sort=newest')
    expect(titles()).toEqual(['Sparse Mixtures', 'Attention Is All You Need'])
  })

  it('applies category, tier and code filters from the URL and counts them on the badge', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second]))
    renderPage('/?category=cs.LG&tier=laptop&code=1')
    expect(titles()).toEqual(['Sparse Mixtures'])
    expect(screen.getByRole('button', { name: 'Filters 3' })).toBeInTheDocument()
    const dialog = openFilters()
    expect(within(dialog).getByLabelText('cs.LG')).toBeChecked()
    expect(within(dialog).getByLabelText('Laptop / CPU')).toBeChecked()
    expect(within(dialog).getByLabelText('Code released')).toBeChecked()
  })

  it('filters as you type and writes the query to the URL after a pause', () => {
    vi.useFakeTimers()
    try {
      mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second]))
      renderPage()
      fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'sparse' } })
      expect(titles()).toEqual(['Sparse Mixtures'])
      expect(screen.getByTestId('search').textContent).toBe('')
      act(() => {
        vi.advanceTimersByTime(150)
      })
      expect(screen.getByTestId('search').textContent).toBe('?q=sparse')
    } finally {
      vi.useRealTimers()
    }
  })

  it('shows a no-match state whose button clears everything, search included', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second]))
    renderPage('/?q=nothing&tier=laptop&sort=newest')
    expect(screen.getByText('No papers match')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show the whole week' }))
    expect(screen.getByTestId('search').textContent).toBe('')
    expect(screen.getByRole('searchbox')).toHaveValue('')
    expect(titles()).toHaveLength(2)
  })

  it('tabs, week selector, filters and clear write to the URL', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem(), second], twoWeeks))
    renderPage('/?q=x')
    fireEvent.click(screen.getByRole('button', { name: 'Newest' }))
    expect(screen.getByTestId('search').textContent).toBe('?q=x&sort=newest')

    fireEvent.change(screen.getByLabelText('Digest week'), { target: { value: '2026-07-27' } })
    expect(screen.getByTestId('search').textContent).toBe('?q=x&sort=newest&week=2026-07-27')
    expect(scrollTo).toHaveBeenCalledWith({ top: 0 })

    const dialog = openFilters()
    fireEvent.click(within(dialog).getByLabelText('cs.LG'))
    fireEvent.click(within(dialog).getByLabelText('Code released'))
    fireEvent.click(within(dialog).getByLabelText('Show dismissed'))
    expect(screen.getByTestId('search').textContent).toBe(
      '?q=x&sort=newest&week=2026-07-27&category=cs.LG&code=1&dismissed=1'
    )
    expect(mockUseFeedWeek).toHaveBeenLastCalledWith({
      week: '2026-07-27',
      include_dismissed: true,
    })
    expect(screen.getByRole('button', { name: 'Filters 3' })).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByTestId('search').textContent).toBe('?q=x&sort=newest&week=2026-07-27')
  })

  it('links to the previous week under the list, keeping the view', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()], twoWeeks))
    renderPage('/?sort=newest')
    const link = screen.getByRole('link', { name: 'Week of Jul 27 (4 papers)' })
    expect(link).toHaveAttribute('href', '/?sort=newest&week=2026-07-27')
    fireEvent.click(link)
    expect(scrollTo).toHaveBeenCalledWith({ top: 0 })
  })

  it('has no previous-week link on the oldest week', () => {
    mockUseFeedWeek.mockReturnValue(
      week([makeFeedItem()], { week_start: '2026-07-27', ...twoWeeks })
    )
    renderPage('/?week=2026-07-27')
    expect(screen.queryByRole('link', { name: /^Week of/ })).not.toBeInTheDocument()
  })

  it('merges profile categories into the category checkboxes', () => {
    mockSession.me = makeMe({
      preferences: {
        feed_profile: {
          categories: ['stat.ML'],
          compute_profile: 'laptop',
          keywords: [],
          weights: null,
        },
      },
    })
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()]))
    renderPage()
    const dialog = openFilters()
    expect(within(dialog).getByLabelText('stat.ML')).toBeInTheDocument()
    expect(within(dialog).getByLabelText('cs.LG')).toBeInTheDocument()
  })

  it('gives each post its own lifecycle with Save and Dismiss only', () => {
    mockUseFeedWeek.mockReturnValue(week([makeFeedItem()]))
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Expand' }))
    expect(usePaperLifecycle).toHaveBeenCalledWith('2401.00001', null)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(lifecycle.dismiss).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(lifecycle.save).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Mark as Implementing' })).not.toBeInTheDocument()
  })
})

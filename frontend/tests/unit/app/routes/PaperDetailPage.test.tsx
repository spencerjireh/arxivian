import { screen, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import PaperDetailPage from '@/app/routes/PaperDetailPage'
import { ApiError } from '@/lib/api-client'
import { makePaperMetadata } from '../../../fixtures/feed'
import { makePaperScoreDetail } from '../../../fixtures/scores'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { lifecycle, resetLifecycle, usePaperLifecycle } from '../../../mocks/lifecycle'
import { mockSession, resetSession } from '../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))
vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

const mockUsePaperScore = vi.fn()
const restartPolling = vi.fn()

vi.mock('@/features/paper/api/get-paper-score', () => ({
  usePaperScore: (id: string, options: unknown) => mockUsePaperScore(id, options),
}))
vi.mock('@/features/paper/hooks/usePaperLifecycle', () => import('../../../mocks/lifecycle'))
vi.mock('@/features/paper/components/ScopedChatPanel', () => ({
  default: ({ arxivId, sessionId }: { arxivId: string; sessionId: string | null }) => (
    <div data-testid="scoped-chat">
      {arxivId}:{sessionId ?? 'new'}
    </div>
  ),
}))

function scoreState(overrides: Record<string, unknown>) {
  return {
    data: undefined,
    isLoading: false,
    error: null,
    pollTimedOut: false,
    restartPolling,
    ...overrides,
  }
}

function renderPage(path = '/papers/2401.00001') {
  return renderWithProviders(
    <Routes>
      <Route path="/papers/:arxivId" element={<PaperDetailPage />} />
    </Routes>,
    { initialEntries: [path] }
  )
}

const pending = { status: 'pending', task_id: 't1', paper: makePaperMetadata() }

beforeEach(() => {
  resetSession()
  mockSession.isSignedIn = true
  resetLifecycle()
  restartPolling.mockClear()
})

describe('PaperDetailPage', () => {
  it('shows a spinner while loading', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ isLoading: true }))
    renderPage()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(mockUsePaperScore).toHaveBeenCalledWith('2401.00001', { poll: true })
  })

  it('shows the pending state and a retry after timeout', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ data: pending }))
    const { unmount } = renderPage()
    expect(screen.getByText(/Ingesting and scoring/)).toBeInTheDocument()
    unmount()
    mockUsePaperScore.mockReturnValue(scoreState({ data: pending, pollTimedOut: true }))
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Check again' }))
    expect(restartPolling).toHaveBeenCalled()
  })

  it('shows an anonymous reader the metadata preview without polling', () => {
    mockSession.isSignedIn = false
    mockUsePaperScore.mockReturnValue(scoreState({ data: { ...pending, task_id: null } }))
    renderPage()
    expect(mockUsePaperScore).toHaveBeenCalledWith('2401.00001', { poll: false })
    expect(screen.getByRole('heading', { name: 'Attention Is All You Need' })).toBeInTheDocument()
    expect(screen.getByText(/We propose a new simple network architecture/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in to score this paper' })).toHaveAttribute(
      'href',
      '/sign-in'
    )
    expect(screen.queryByText(/Ingesting and scoring/)).not.toBeInTheDocument()
  })

  it('gives an anonymous reader the evidence, a sign-in Save and a chat prompt', () => {
    mockSession.isSignedIn = false
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage()
    expect(screen.getAllByText('Strong').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Algorithm 1/).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Save' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('button', { name: 'Dismiss' })).not.toBeInTheDocument()
    expect(screen.queryByTestId('scoped-chat')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in to chat' })).toHaveAttribute(
      'href',
      '/sign-in'
    )
  })

  it('shows not found on 404', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ error: new ApiError(404, 'Not Found', 'nope') }))
    renderPage('/papers/9999.99999')
    expect(screen.getByText('Paper not found')).toBeInTheDocument()
  })

  it('renders the header, summary, four open dimension rows and closed details when ready', () => {
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage()
    expect(screen.getByRole('heading', { name: 'Attention Is All You Need' })).toBeInTheDocument()
    expect(screen.getByText('Transformer for machine translation')).toBeInTheDocument()
    expect(screen.getByText('machine translation')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Method clarity' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Demand' })).toBeInTheDocument()
    expect(screen.getByText('Scoring details').closest('details')).not.toHaveAttribute('open')
    expect(screen.getByRole('link', { name: /Back to feed/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('button', { name: 'Mark as Implementing' })).toBeInTheDocument()
  })

  it('binds the header actions to the route arXiv id', () => {
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage()
    expect(usePaperLifecycle).toHaveBeenCalledWith('2401.00001', null)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(lifecycle.save).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(lifecycle.dismiss).toHaveBeenCalledTimes(1)
  })

  it('mounts the scoped chat panel only when ready, with the session from the URL', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ data: pending }))
    const { unmount } = renderPage()
    expect(screen.queryByTestId('scoped-chat')).not.toBeInTheDocument()
    unmount()
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage('/papers/2401.00001?session=abc')
    expect(screen.getByTestId('scoped-chat')).toHaveTextContent('2401.00001:abc')
  })
})

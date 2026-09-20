import { screen, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import PaperDetailPage from '../../../src/pages/PaperDetailPage'
import { ApiError } from '../../../src/api/client'
import { makePaperScoreDetail } from '../../fixtures/scores'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

const mockUsePaperScore = vi.fn()
const setMutateAsync = vi.fn().mockResolvedValue({})
const clearMutateAsync = vi.fn().mockResolvedValue(undefined)
const restartPolling = vi.fn()

vi.mock('../../../src/api/scores', () => ({
  usePaperScore: (id: string) => mockUsePaperScore(id),
}))
vi.mock('../../../src/api/paperStates', () => ({
  useSetPaperState: () => ({ mutateAsync: setMutateAsync }),
  useClearPaperState: () => ({ mutateAsync: clearMutateAsync }),
}))
vi.mock('../../../src/components/paper/ScopedChatPanel', () => ({
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

beforeEach(() => {
  setMutateAsync.mockClear()
  clearMutateAsync.mockClear()
  restartPolling.mockClear()
})

describe('PaperDetailPage', () => {
  it('shows a spinner while loading', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ isLoading: true }))
    renderPage()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(mockUsePaperScore).toHaveBeenCalledWith('2401.00001')
  })

  it('shows the pending state and a retry after timeout', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ data: { status: 'pending', task_id: 't1' } }))
    const { unmount } = renderPage()
    expect(screen.getByText(/Ingesting and scoring/)).toBeInTheDocument()
    unmount()
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'pending', task_id: 't1' }, pollTimedOut: true })
    )
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Check again' }))
    expect(restartPolling).toHaveBeenCalled()
  })

  it('shows not found on 404', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ error: new ApiError(404, 'Not Found', 'nope') }))
    renderPage('/papers/9999.99999')
    expect(screen.getByText('Paper not found')).toBeInTheDocument()
  })

  it('renders the header, chips and four dimension rows when ready', () => {
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage()
    expect(screen.getByRole('heading', { name: 'Attention Is All You Need' })).toBeInTheDocument()
    expect(screen.getByText('machine translation')).toBeInTheDocument()
    expect(screen.getByText('Method clarity')).toBeInTheDocument()
    expect(screen.getByText('Demand')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to feed/ })).toHaveAttribute('href', '/feed')
  })

  it('save and dismiss mutate with the route arXiv id', () => {
    mockUsePaperScore.mockReturnValue(
      scoreState({ data: { status: 'ready', detail: makePaperScoreDetail() } })
    )
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(setMutateAsync).toHaveBeenCalledWith({ arxivId: '2401.00001', body: { state: 'saved' } })
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(setMutateAsync).toHaveBeenCalledWith({
      arxivId: '2401.00001',
      body: { state: 'dismissed' },
    })
  })

  it('mounts the scoped chat panel only when ready, with the session from the URL', () => {
    mockUsePaperScore.mockReturnValue(scoreState({ data: { status: 'pending', task_id: 't1' } }))
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

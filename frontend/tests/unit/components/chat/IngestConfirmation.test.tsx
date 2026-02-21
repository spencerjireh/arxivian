import { act } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IngestConfirmation from '../../../../src/components/chat/IngestConfirmation'
import { useChatStore } from '../../../../src/stores/chatStore'
import type { ConfirmIngestEventData } from '../../../../src/types/api'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

const mockProposal: ConfirmIngestEventData = {
  papers: [
    {
      arxiv_id: '2401.00001',
      title: 'Paper One',
      authors: ['Author A', 'Author B'],
      abstract: 'Abstract one',
      published_date: '2024-01-15',
    },
    {
      arxiv_id: '2401.00002',
      title: 'Paper Two',
      authors: ['Author C'],
      abstract: 'Abstract two',
    },
  ],
  session_id: 'sess-1',
  thread_id: 'thread-1',
}

/** Render inside act() to flush Zustand useSyncExternalStore microtasks. */
async function renderIngestConfirmation(
  props: Partial<Parameters<typeof IngestConfirmation>[0]> = {},
) {
  let result: ReturnType<typeof render>
  await act(async () => {
    result = render(
      <IngestConfirmation
        proposal={mockProposal}
        onConfirm={vi.fn()}
        {...props}
      />,
    )
  })
  return result!
}

describe('IngestConfirmation', () => {
  beforeEach(() => {
    // Pre-seed the store with all papers selected (mirrors real flow where
    // sendMessage's onConfirmIngest initializes selectedIngestIds).
    // Use setState() directly to avoid triggering subscriber notifications outside act().
    useChatStore.setState({
      selectedIngestIds: new Set(mockProposal.papers.map((p) => p.arxiv_id)),
    })
  })

  afterEach(() => {
    // Unmount component first so Zustand subscribers are removed before
    // resetting state -- prevents act() warnings from out-of-scope re-renders.
    cleanup()
    useChatStore.setState({
      ingestProposal: null,
      isIngesting: false,
      selectedIngestIds: null,
    })
  })

  it('renders paper titles and arxiv ids', async () => {
    await renderIngestConfirmation()

    expect(screen.getByText('Paper One')).toBeInTheDocument()
    expect(screen.getByText('Paper Two')).toBeInTheDocument()
    expect(screen.getByText('2401.00001')).toBeInTheDocument()
    expect(screen.getByText('2401.00002')).toBeInTheDocument()
  })

  it('all papers selected by default', async () => {
    await renderIngestConfirmation()

    // The confirm button should show the total count when all are selected
    expect(screen.getByText('Add 2 to library')).toBeInTheDocument()
    // The header should offer "Deselect all" when all are selected
    expect(screen.getByText('Deselect all')).toBeInTheDocument()
  })

  it('clicking a paper toggles its selection', async () => {
    const user = userEvent.setup()
    await renderIngestConfirmation()

    // Initially all selected: "Add 2 to library"
    expect(screen.getByText('Add 2 to library')).toBeInTheDocument()

    // Click on the first paper to deselect it
    await user.click(screen.getByText('Paper One'))

    // Now only 1 selected: "Add 1 to library"
    expect(screen.getByText('Add 1 to library')).toBeInTheDocument()

    // Header should now show "Select all" instead of "Deselect all"
    expect(screen.getByText('Select all')).toBeInTheDocument()
  })

  it('Add to library calls onConfirm with selected ids', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    await renderIngestConfirmation({ onConfirm })

    // All papers selected by default, click confirm
    await user.click(screen.getByText('Add 2 to library'))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onConfirm).toHaveBeenCalledWith(true, ['2401.00001', '2401.00002'])
  })

  it('Cancel calls onConfirm with declined', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    await renderIngestConfirmation({ onConfirm })

    await user.click(screen.getByText('Cancel'))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onConfirm).toHaveBeenCalledWith(false, [])
  })

  it('shows loading state when isIngesting', async () => {
    await renderIngestConfirmation({ isIngesting: true })

    expect(screen.getByText('Adding to library...')).toBeInTheDocument()
  })

  it('shows resolved state when isResolved', async () => {
    await renderIngestConfirmation({ isResolved: true, ingestDeclined: false })

    expect(screen.getByText('Added to library')).toBeInTheDocument()
  })

  it('hides action buttons when resolved', async () => {
    await renderIngestConfirmation({ isResolved: true })

    expect(screen.queryByText('Cancel')).not.toBeInTheDocument()
    expect(screen.queryByText(/Add .* to library/)).not.toBeInTheDocument()
  })

  it('shows cancelled state when resolved and declined', async () => {
    await renderIngestConfirmation({ isResolved: true, ingestDeclined: true })

    expect(screen.getByText('Cancelled')).toBeInTheDocument()
    expect(screen.queryByText('Added to library')).not.toBeInTheDocument()
  })

  it('shows added to library when resolved and approved', async () => {
    await renderIngestConfirmation({ isResolved: true, ingestDeclined: false })

    expect(screen.getByText('Added to library')).toBeInTheDocument()
    expect(screen.queryByText('Cancelled')).not.toBeInTheDocument()
  })

  it('hides checkboxes when resolved', async () => {
    await renderIngestConfirmation({ isResolved: true, ingestDeclined: false })

    // Checkboxes should not be rendered when resolved
    const checkboxes = screen.queryAllByRole('checkbox')
    expect(checkboxes).toHaveLength(0)
  })
})

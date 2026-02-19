import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import IngestConfirmation from '../../../../src/components/chat/IngestConfirmation'
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

describe('IngestConfirmation', () => {
  it('renders paper titles and arxiv ids', () => {
    renderWithProviders(
      <IngestConfirmation proposal={mockProposal} onConfirm={vi.fn()} />,
    )

    expect(screen.getByText('Paper One')).toBeInTheDocument()
    expect(screen.getByText('Paper Two')).toBeInTheDocument()
    expect(screen.getByText('2401.00001')).toBeInTheDocument()
    expect(screen.getByText('2401.00002')).toBeInTheDocument()
  })

  it('all papers selected by default', () => {
    renderWithProviders(
      <IngestConfirmation proposal={mockProposal} onConfirm={vi.fn()} />,
    )

    // The confirm button should show the total count when all are selected
    expect(screen.getByText('Add 2 to library')).toBeInTheDocument()
    // The header should offer "Deselect all" when all are selected
    expect(screen.getByText('Deselect all')).toBeInTheDocument()
  })

  it('clicking a paper toggles its selection', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <IngestConfirmation proposal={mockProposal} onConfirm={vi.fn()} />,
    )

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

    renderWithProviders(
      <IngestConfirmation proposal={mockProposal} onConfirm={onConfirm} />,
    )

    // All papers selected by default, click confirm
    await user.click(screen.getByText('Add 2 to library'))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onConfirm).toHaveBeenCalledWith(true, ['2401.00001', '2401.00002'])
  })

  it('Skip calls onConfirm with declined', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    renderWithProviders(
      <IngestConfirmation proposal={mockProposal} onConfirm={onConfirm} />,
    )

    await user.click(screen.getByText('Skip'))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onConfirm).toHaveBeenCalledWith(false, [])
  })

  it('shows loading state when isIngesting', () => {
    renderWithProviders(
      <IngestConfirmation
        proposal={mockProposal}
        onConfirm={vi.fn()}
        isIngesting={true}
      />,
    )

    expect(screen.getByText('Adding to library...')).toBeInTheDocument()
  })

  it('shows resolved state when isResolved', () => {
    renderWithProviders(
      <IngestConfirmation
        proposal={mockProposal}
        onConfirm={vi.fn()}
        isResolved={true}
      />,
    )

    expect(screen.getByText('Added to library')).toBeInTheDocument()
  })

  it('hides action buttons when resolved', () => {
    renderWithProviders(
      <IngestConfirmation
        proposal={mockProposal}
        onConfirm={vi.fn()}
        isResolved={true}
      />,
    )

    expect(screen.queryByText('Skip')).not.toBeInTheDocument()
    expect(screen.queryByText(/Add .* to library/)).not.toBeInTheDocument()
  })
})

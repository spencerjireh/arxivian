import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import PaperCard from '../../../../src/components/library/PaperCard'
import type { PaperListItem } from '../../../../src/types/api'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

const samplePaper: PaperListItem = {
  arxiv_id: '2401.00001',
  title: 'Attention Is All You Need',
  authors: ['Vaswani', 'Shazeer', 'Parmar'],
  abstract: 'A novel architecture based on attention mechanisms.',
  categories: ['cs.CL', 'cs.AI'],
  published_date: '2024-01-15',
  pdf_url: 'https://arxiv.org/pdf/2401.00001',
  sections: null,
  pdf_processed: true,
  pdf_processing_date: null,
  parser_used: null,
  created_at: '2024-01-15',
  updated_at: '2024-01-15',
}

describe('PaperCard', () => {
  const onDelete = vi.fn()

  beforeEach(() => {
    onDelete.mockClear()
  })

  it('renders title, authors, arXiv ID, and categories', () => {
    renderWithProviders(
      <PaperCard paper={samplePaper} onDelete={onDelete} isDeleting={false} />,
    )

    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    expect(screen.getByText('Vaswani, Shazeer, Parmar')).toBeInTheDocument()
    expect(screen.getByText('2401.00001')).toBeInTheDocument()
    expect(screen.getByText('cs.CL')).toBeInTheDocument()
    expect(screen.getByText('cs.AI')).toBeInTheDocument()
  })

  it('shows confirm/cancel on delete click', () => {
    renderWithProviders(
      <PaperCard paper={samplePaper} onDelete={onDelete} isDeleting={false} />,
    )

    const deleteButton = screen.getByLabelText('Delete paper')
    fireEvent.click(deleteButton)

    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('calls onDelete with correct ID on confirm', () => {
    renderWithProviders(
      <PaperCard paper={samplePaper} onDelete={onDelete} isDeleting={false} />,
    )

    fireEvent.click(screen.getByLabelText('Delete paper'))
    fireEvent.click(screen.getByText('Confirm'))

    expect(onDelete).toHaveBeenCalledWith('2401.00001')
  })

  it('hides confirmation on cancel', () => {
    renderWithProviders(
      <PaperCard paper={samplePaper} onDelete={onDelete} isDeleting={false} />,
    )

    fireEvent.click(screen.getByLabelText('Delete paper'))
    expect(screen.getByText('Confirm')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByText('Confirm')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Delete paper')).toBeInTheDocument()
  })

  it('has target="_blank" and no rel attribute on PDF link', () => {
    renderWithProviders(
      <PaperCard paper={samplePaper} onDelete={onDelete} isDeleting={false} />,
    )

    const pdfLink = screen.getByText('PDF').closest('a')
    expect(pdfLink).toHaveAttribute('target', '_blank')
    expect(pdfLink).not.toHaveAttribute('rel')
  })
})

import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import LibraryPage from '../../../src/pages/LibraryPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

const mockUsePapers = vi.fn()

vi.mock('../../../src/api/papers', () => ({
  usePapers: () => mockUsePapers(),
}))

const samplePapers = [
  {
    arxiv_id: '2401.00001',
    title: 'Test Paper One',
    authors: ['Alice', 'Bob'],
    abstract: 'Abstract one',
    categories: ['cs.AI'],
    published_date: '2024-01-01',
    pdf_url: 'https://arxiv.org/pdf/2401.00001',
    sections: null,
    pdf_processed: true,
    pdf_processing_date: null,
    parser_used: null,
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
  },
]

describe('LibraryPage', () => {
  it('shows loading spinner', () => {
    mockUsePapers.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    })

    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('Library')).toBeInTheDocument()
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('shows error message on query failure', () => {
    mockUsePapers.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    })

    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('shows empty state when no papers', () => {
    mockUsePapers.mockReturnValue({
      data: { total: 0, offset: 0, limit: 20, papers: [] },
      isLoading: false,
      error: null,
    })

    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('No papers in the knowledge base yet')).toBeInTheDocument()
  })

  it('renders paper cards when data is available', () => {
    mockUsePapers.mockReturnValue({
      data: { total: 1, offset: 0, limit: 20, papers: samplePapers },
      isLoading: false,
      error: null,
    })

    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('Test Paper One')).toBeInTheDocument()
    expect(screen.getByText('1 paper')).toBeInTheDocument()
  })

  it('renders pagination when total exceeds page size', () => {
    mockUsePapers.mockReturnValue({
      data: { total: 25, offset: 0, limit: 20, papers: samplePapers },
      isLoading: false,
      error: null,
    })

    renderWithProviders(<LibraryPage />)

    expect(screen.getByText('Previous')).toBeInTheDocument()
    expect(screen.getByText('Next')).toBeInTheDocument()
    expect(screen.getByText('1-20 of 25')).toBeInTheDocument()
  })
})

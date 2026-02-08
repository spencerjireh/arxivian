import { screen, waitFor, fireEvent, act } from '@testing-library/react'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import SettingsPage from '../../../src/pages/SettingsPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

const mockPrefsData = {
  arxiv_searches: [
    { name: 'Transformers', query: 'transformer attention', max_results: 10 },
    { name: 'LLMs', query: 'large language models', categories: ['cs.CL'], max_results: 20 },
  ],
  notification_settings: { email_digest: false },
}

const mockUsePreferences = vi.fn()
const mockUseAddArxivSearch = vi.fn()
const mockUseDeleteArxivSearch = vi.fn()

vi.mock('../../../src/api/preferences', () => ({
  usePreferences: () => mockUsePreferences(),
  useAddArxivSearch: () => mockUseAddArxivSearch(),
  useDeleteArxivSearch: () => mockUseDeleteArxivSearch(),
}))

function setupDefaultMutations() {
  mockUseAddArxivSearch.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  })
  mockUseDeleteArxivSearch.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    variables: null,
  })
}

describe('SettingsPage', () => {
  beforeEach(() => {
    setupDefaultMutations()
  })

  it('shows spinner when loading', () => {
    mockUsePreferences.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    })

    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('Settings')).toBeInTheDocument()
    const spinner = document.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('shows error message when preferences query fails', () => {
    mockUsePreferences.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    })

    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('Unable to load saved searches')).toBeInTheDocument()
  })

  it('shows empty state when no saved searches', () => {
    mockUsePreferences.mockReturnValue({
      data: { arxiv_searches: [], notification_settings: { email_digest: false } },
      isLoading: false,
      error: null,
    })

    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('No saved searches')).toBeInTheDocument()
  })

  it('renders search list when data is available', () => {
    mockUsePreferences.mockReturnValue({
      data: mockPrefsData,
      isLoading: false,
      error: null,
    })

    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('Transformers')).toBeInTheDocument()
    expect(screen.getByText('LLMs')).toBeInTheDocument()
  })

  it('shows inline error when add mutation fails', async () => {
    mockUsePreferences.mockReturnValue({
      data: { arxiv_searches: [], notification_settings: { email_digest: false } },
      isLoading: false,
      error: null,
    })

    // Capture the onError callback when mutate is called
    let capturedOnError: ((err: Error) => void) | undefined
    mockUseAddArxivSearch.mockReturnValue({
      mutate: vi.fn((_config: unknown, opts?: { onError?: (err: Error) => void }) => {
        capturedOnError = opts?.onError
      }),
      isPending: false,
    })

    renderWithProviders(<SettingsPage />)

    // Open the add form
    fireEvent.click(screen.getByText('Add search'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search name')).toBeInTheDocument()
    })

    // Fill in form fields
    fireEvent.change(screen.getByPlaceholderText('Search name'), {
      target: { value: 'Test Search' },
    })
    fireEvent.change(screen.getByPlaceholderText('Query (e.g. transformer attention)'), {
      target: { value: 'test query' },
    })

    // Click save to trigger mutate
    fireEvent.click(screen.getByText('Save'))

    // Simulate the mutation error callback
    expect(capturedOnError).toBeDefined()
    act(() => {
      capturedOnError!(new Error('Server error'))
    })

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument()
    })
  })
})

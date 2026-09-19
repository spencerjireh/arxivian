import { screen, fireEvent, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import OnboardingPage from '../../../src/pages/OnboardingPage'
import { useUserStore } from '../../../src/stores/userStore'

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

const mutate = vi.fn()
vi.mock('../../../src/api/users', () => ({
  useUpdateFeedProfile: () => ({ mutate, isPending: false }),
}))

const base = {
  id: 'u', email: null, first_name: null, last_name: null, tier: 'free' as const,
  daily_chat_limit: null, chats_used_today: 0, can_adjust_settings: true,
  daily_ingest_limit: null, ingests_used_today: 0, can_view_execution_details: false,
}

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/feed" element={<div>feed page</div>} />
    </Routes>,
    { initialEntries: ['/onboarding'] },
  )
}

afterEach(() => {
  useUserStore.setState({ me: null })
  mutate.mockReset()
})

describe('OnboardingPage', () => {
  it('redirects an onboarded user to the feed', () => {
    useUserStore.setState({ me: { ...base, onboarded: true } })
    renderPage()
    expect(screen.getByText('feed page')).toBeInTheDocument()
  })

  it('submits the profile and navigates to the feed on success', async () => {
    useUserStore.setState({ me: { ...base, onboarded: false } })
    mutate.mockImplementation((_profile, opts: { onSuccess: () => void }) => opts.onSuccess())
    renderPage()
    expect(screen.getByText('Shape your first digest')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /cs\.AI/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Laptop/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Build my feed' }))
    expect(mutate).toHaveBeenCalledWith(
      { categories: ['cs.AI'], compute_profile: 'laptop', keywords: [] },
      expect.any(Object),
    )
    await waitFor(() => expect(screen.getByText('feed page')).toBeInTheDocument())
  })
})

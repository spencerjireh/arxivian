import { screen, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import OnboardingPage from '@/app/routes/OnboardingPage'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { makeMe, mockSession, resetSession } from '../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))
vi.mock('@/lib/notifications', () => ({ notify: { error: vi.fn(), success: vi.fn() } }))

const mutate = vi.fn()
vi.mock('@/features/profile/api/update-feed-profile', () => ({
  useUpdateFeedProfile: () => ({ mutate, isPending: false }),
}))

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route path="/" element={<div>feed page</div>} />
    </Routes>,
    { initialEntries: ['/onboarding'] }
  )
}

afterEach(() => {
  resetSession()
  mutate.mockReset()
})

describe('OnboardingPage', () => {
  it('redirects an onboarded user to the feed', () => {
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ onboarded: true })
    renderPage()
    expect(screen.getByText('feed page')).toBeInTheDocument()
  })

  it('submits the profile and navigates to the feed on success', async () => {
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ onboarded: false })
    mutate.mockImplementation((_profile, opts: { onSuccess: () => void }) => opts.onSuccess())
    renderPage()
    expect(screen.getByText('Shape your first digest')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /cs\.AI/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Laptop/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Build my feed' }))
    expect(mutate).toHaveBeenCalledWith(
      { categories: ['cs.AI'], compute_profile: 'laptop', keywords: [] },
      expect.any(Object)
    )
    expect(await screen.findByText('feed page')).toBeInTheDocument()
  })
})

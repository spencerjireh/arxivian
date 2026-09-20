import { screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import OnboardingGate from '../../../../src/components/auth/OnboardingGate'
import { useUserStore } from '../../../../src/stores/userStore'

const base = {
  id: 'u',
  email: null,
  first_name: null,
  last_name: null,
  tier: 'free' as const,
  daily_chat_limit: null,
  chats_used_today: 0,
}

function renderAt(path: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/onboarding" element={<div>onboarding page</div>} />
      <Route
        path="*"
        element={
          <OnboardingGate>
            <div>protected content</div>
          </OnboardingGate>
        }
      />
    </Routes>,
    { initialEntries: [path] }
  )
}

afterEach(() => {
  useUserStore.setState({ me: null })
})

describe('OnboardingGate', () => {
  it('renders children while me is unknown (fails open)', () => {
    renderAt('/feed')
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })

  it('redirects a user without a profile to /onboarding', () => {
    useUserStore.setState({ me: { ...base, onboarded: false } })
    renderAt('/feed')
    expect(screen.getByText('onboarding page')).toBeInTheDocument()
  })

  it('renders children for an onboarded user', () => {
    useUserStore.setState({ me: { ...base, onboarded: true } })
    renderAt('/feed')
    expect(screen.getByText('protected content')).toBeInTheDocument()
  })

  it('does not loop when already on /onboarding', () => {
    useUserStore.setState({ me: { ...base, onboarded: false } })
    renderWithProviders(
      <Routes>
        <Route
          path="/onboarding"
          element={
            <OnboardingGate>
              <div>onboarding page</div>
            </OnboardingGate>
          }
        />
      </Routes>,
      { initialEntries: ['/onboarding'] }
    )
    expect(screen.getByText('onboarding page')).toBeInTheDocument()
  })
})

import { screen, fireEvent } from '@testing-library/react'
import OnboardingPrompt, {
  ONBOARDING_PROMPT_KEY,
} from '@/features/feed/components/OnboardingPrompt'
import { renderWithProviders } from '../../../../helpers/renderWithProviders'
import { makeMe, mockSession, resetSession } from '../../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../../mocks/auth'))

afterEach(() => {
  resetSession()
  localStorage.removeItem(ONBOARDING_PROMPT_KEY)
})

describe('OnboardingPrompt', () => {
  it('renders nothing for an anonymous reader or an onboarded one', () => {
    const { unmount } = renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    unmount()
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ onboarded: true })
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  })

  it('prompts a signed-in reader without a profile and links to the form', () => {
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ onboarded: false })
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.getByRole('complementary', { name: 'Set up your feed' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Set up' })).toHaveAttribute('href', '/onboarding')
  })

  it('stays dismissed for the browser after Dismiss', () => {
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ onboarded: false })
    const { unmount } = renderWithProviders(<OnboardingPrompt />)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_PROMPT_KEY)).toBe('1')
    unmount()
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  })
})

import { screen, fireEvent } from '@testing-library/react'
import OnboardingPrompt, {
  ONBOARDING_PROMPT_KEY,
} from '@/features/feed/components/OnboardingPrompt'
import { useUserStore } from '@/stores/userStore'
import { renderWithProviders } from '../../../../helpers/renderWithProviders'

const base = {
  id: 'u',
  email: null,
  first_name: null,
  last_name: null,
  tier: 'free' as const,
  daily_chat_limit: 10,
  chats_used_today: 0,
}

afterEach(() => {
  useUserStore.setState({ me: null })
  localStorage.removeItem(ONBOARDING_PROMPT_KEY)
})

describe('OnboardingPrompt', () => {
  it('renders nothing for an anonymous reader or an onboarded one', () => {
    const { unmount } = renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    unmount()
    useUserStore.setState({ me: { ...base, onboarded: true } })
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  })

  it('prompts a signed-in reader without a profile and links to the form', () => {
    useUserStore.setState({ me: { ...base, onboarded: false } })
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.getByRole('complementary', { name: 'Set up your feed' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Set up' })).toHaveAttribute('href', '/onboarding')
  })

  it('stays dismissed for the browser after Dismiss', () => {
    useUserStore.setState({ me: { ...base, onboarded: false } })
    const { unmount } = renderWithProviders(<OnboardingPrompt />)
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
    expect(localStorage.getItem(ONBOARDING_PROMPT_KEY)).toBe('1')
    unmount()
    renderWithProviders(<OnboardingPrompt />)
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument()
  })
})

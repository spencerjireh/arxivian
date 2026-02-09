import { screen } from '@testing-library/react'
import { mockAuth } from '../../mocks/clerk'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import { useUserStore } from '../../../src/stores/userStore'
import PricingPage from '../../../src/pages/PricingPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

describe('PricingPage', () => {
  beforeEach(() => {
    mockAuth.isSignedIn = false
    useUserStore.setState({ me: null })
  })

  it('renders heading and both tier cards', () => {
    renderWithProviders(<PricingPage />)

    expect(screen.getByRole('heading', { name: /Simple, transparent pricing/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Free' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pro' })).toBeInTheDocument()
  })

  it('shows Start for free link when unauthenticated', () => {
    renderWithProviders(<PricingPage />)

    expect(screen.getByText('Start for free')).toBeInTheDocument()
  })

  it('shows Current plan on Free card when authenticated as free-tier user', () => {
    mockAuth.isSignedIn = true
    useUserStore.setState({
      me: {
        id: 'u1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        tier: 'free',
        daily_chat_limit: 20,
        chats_used_today: 0,
        can_select_model: false,
      },
    })

    renderWithProviders(<PricingPage />)

    const btn = screen.getByText('Current plan')
    expect(btn).toBeInTheDocument()
    expect(btn.closest('button')).toBeDisabled()
  })

  it('shows Contact us mailto link on Pro card', () => {
    renderWithProviders(<PricingPage />)

    const link = screen.getByRole('link', { name: /Contact us/ })
    expect(link).toHaveAttribute('href', expect.stringContaining('mailto:'))
  })
})

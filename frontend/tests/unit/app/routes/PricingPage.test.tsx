import { screen } from '@testing-library/react'
import PricingPage from '@/app/routes/PricingPage'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { makeMe, mockSession, resetSession } from '../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))
vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

describe('PricingPage', () => {
  beforeEach(() => {
    resetSession()
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
    mockSession.isSignedIn = true
    mockSession.me = makeMe({ tier: 'free' })

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

import { screen } from '@testing-library/react'
import AboutPage from '@/app/routes/AboutPage'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { mockSession, resetSession } from '../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))
vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

describe('AboutPage', () => {
  beforeEach(() => {
    resetSession()
  })

  it('renders the hero with the feed and sign-up calls to action when signed out', () => {
    renderWithProviders(<AboutPage />, { initialEntries: ['/about'] })
    expect(screen.getByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open the feed/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /Get started/ })).toHaveAttribute('href', '/sign-up')
    expect(screen.getByRole('link', { name: /See plans/ })).toHaveAttribute('href', '/pricing')
  })

  it('drops the sign-up call to action when signed in and never redirects', () => {
    mockSession.isSignedIn = true
    renderWithProviders(<AboutPage />, { initialEntries: ['/about'] })
    expect(screen.getByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open the feed/ })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: /Get started/ })).not.toBeInTheDocument()
  })
})

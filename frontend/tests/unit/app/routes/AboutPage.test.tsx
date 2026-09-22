import { screen } from '@testing-library/react'
import AboutPage from '@/app/routes/AboutPage'
import { mockAuth } from '../../../mocks/clerk'
import { renderWithProviders } from '../../../helpers/renderWithProviders'

vi.mock('@clerk/clerk-react', () => import('../../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

describe('AboutPage', () => {
  beforeEach(() => {
    mockAuth.isSignedIn = false
  })

  it('renders the hero with the feed and sign-up calls to action when signed out', () => {
    renderWithProviders(<AboutPage />, { initialEntries: ['/about'] })
    expect(screen.getByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open the feed/ })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /Get started/ })).toHaveAttribute('href', '/sign-up')
    expect(screen.getByRole('link', { name: /See plans/ })).toHaveAttribute('href', '/pricing')
  })

  it('drops the sign-up call to action when signed in and never redirects', () => {
    mockAuth.isSignedIn = true
    renderWithProviders(<AboutPage />, { initialEntries: ['/about'] })
    expect(screen.getByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open the feed/ })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: /Get started/ })).not.toBeInTheDocument()
  })
})

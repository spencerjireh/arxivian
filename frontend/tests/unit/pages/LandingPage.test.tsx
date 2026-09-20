import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { mockAuth } from '../../mocks/clerk'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import LandingPage from '../../../src/pages/LandingPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

describe('LandingPage', () => {
  beforeEach(() => {
    mockAuth.isSignedIn = false
  })

  it('renders hero and Get started CTA when unauthenticated', () => {
    renderWithProviders(<LandingPage />)

    expect(screen.getByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
    // "Get started" appears in both nav and hero CTA
    const buttons = screen.getAllByText('Get started')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
  })

  it('shows Open feed when authenticated', () => {
    mockAuth.isSignedIn = true

    renderWithProviders(<LandingPage />)

    expect(screen.getAllByText('Open feed').length).toBeGreaterThanOrEqual(1)
  })

  it('shows See plans link to /pricing when unauthenticated', () => {
    renderWithProviders(<LandingPage />)

    const link = screen.getByRole('link', { name: /See plans/ })
    expect(link).toHaveAttribute('href', '/pricing')
  })

  it('redirects to /feed when authenticated', async () => {
    mockAuth.isSignedIn = true

    renderWithProviders(
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/feed" element={<div data-testid="feed-page">Feed</div>} />
      </Routes>,
      { initialEntries: ['/'] }
    )

    await waitFor(() => {
      expect(screen.getByTestId('feed-page')).toBeInTheDocument()
    })
  })
})

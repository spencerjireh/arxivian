import { screen, waitFor } from '@testing-library/react'
import { mockAuth } from '../../mocks/clerk'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import { Routes, Route } from 'react-router-dom'
import LandingPage from '../../../src/pages/LandingPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

describe('LandingPage', () => {
  beforeEach(() => {
    mockAuth.isSignedIn = false
  })

  it('renders hero and Get started CTA when unauthenticated', () => {
    renderWithProviders(<LandingPage />)

    expect(screen.getByRole('heading', { name: /Navigate the arXiv/ })).toBeInTheDocument()
    // "Get started" appears in both nav and hero CTA
    const buttons = screen.getAllByText('Get started')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
  })

  it('shows Go to Chat button when authenticated', () => {
    mockAuth.isSignedIn = true

    renderWithProviders(<LandingPage />)

    expect(screen.getByText('Go to Chat')).toBeInTheDocument()
  })

  it('redirects to /chat when authenticated', async () => {
    mockAuth.isSignedIn = true

    renderWithProviders(
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/chat" element={<div data-testid="chat-page">Chat</div>} />
      </Routes>,
      { initialEntries: ['/'] },
    )

    await waitFor(() => {
      expect(screen.getByTestId('chat-page')).toBeInTheDocument()
    })
  })
})

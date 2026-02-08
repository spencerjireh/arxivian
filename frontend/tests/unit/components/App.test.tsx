import { render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

// Stub protected route to render children directly in tests
vi.mock('../../../src/components/auth/ProtectedRoute', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('App routes', () => {
  it('redirects unknown paths to /', async () => {
    const { routes } = await import('../../../src/App')

    const router = createMemoryRouter(routes, {
      initialEntries: ['/nonexistent'],
    })

    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/')
    })
  })

  it('renders LandingPage at /', async () => {
    const { routes } = await import('../../../src/App')

    const router = createMemoryRouter(routes, {
      initialEntries: ['/'],
    })

    render(<RouterProvider router={router} />)

    await waitFor(() => {
      expect(screen.getByText(/Navigate the arXiv/)).toBeInTheDocument()
    })
  })
})

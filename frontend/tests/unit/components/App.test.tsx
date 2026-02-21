import { act } from 'react'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

// Stub protected route to render children directly in tests
vi.mock('../../../src/components/auth/ProtectedRoute', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('App routes', () => {
  it('shows 404 page for unknown paths', async () => {
    const { routes } = await import('../../../src/App')

    const router = createMemoryRouter(routes, {
      initialEntries: ['/nonexistent'],
    })

    await act(async () => {
      render(<RouterProvider router={router} />)
    })

    expect(screen.getByText('Page not found')).toBeInTheDocument()
  })

  it('renders LandingPage at /', async () => {
    const { routes } = await import('../../../src/App')

    const router = createMemoryRouter(routes, {
      initialEntries: ['/'],
    })

    await act(async () => {
      render(<RouterProvider router={router} />)
    })

    expect(
      await screen.findByRole('heading', { name: /Understand research/ }),
    ).toBeInTheDocument()
  })

  it('renders PricingPage at /pricing', async () => {
    const { routes } = await import('../../../src/App')

    const router = createMemoryRouter(routes, {
      initialEntries: ['/pricing'],
    })

    await act(async () => {
      render(<RouterProvider router={router} />)
    })

    expect(
      await screen.findByRole('heading', { name: /Simple, transparent pricing/ }),
    ).toBeInTheDocument()
  })
})

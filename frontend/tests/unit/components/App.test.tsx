import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

// Stub protected route to render children directly in tests
vi.mock('../../../src/components/auth/ProtectedRoute', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

// Mock lazy-loaded pages with lightweight stubs so the route tests
// verify routing logic only -- page rendering is covered by page-level tests.
vi.mock('../../../src/pages/LandingPage', () => ({
  default: () => <h1>Understand research</h1>,
}))
vi.mock('../../../src/pages/PricingPage', () => ({
  default: () => <h1>Simple, transparent pricing</h1>,
}))
vi.mock('../../../src/pages/NotFoundPage', () => ({
  default: () => <div>Page not found</div>,
}))

// Eagerly resolve the App module (and all transitive non-mocked imports)
// before any test runs, so the first test doesn't pay the cold-start cost
// that would push React.lazy resolution past findBy* timeouts.
let routes: RouteObject[]
beforeAll(async () => {
  const mod = await import('../../../src/App')
  routes = mod.routes
})

describe('App routes', () => {
  it('shows 404 page for unknown paths', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/nonexistent'],
    })

    render(<RouterProvider router={router} />)

    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })

  it('renders LandingPage at /', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/'],
    })

    render(<RouterProvider router={router} />)

    expect(
      await screen.findByRole('heading', { name: /Understand research/ }),
    ).toBeInTheDocument()
  })

  it('renders PricingPage at /pricing', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/pricing'],
    })

    render(<RouterProvider router={router} />)

    expect(
      await screen.findByRole('heading', { name: /Simple, transparent pricing/ }),
    ).toBeInTheDocument()
  })
})

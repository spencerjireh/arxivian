import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
  default: () => <h1>Papers you could</h1>,
}))
vi.mock('../../../src/pages/PricingPage', () => ({
  default: () => <h1>Simple, transparent pricing</h1>,
}))
vi.mock('../../../src/pages/NotFoundPage', () => ({
  default: () => <div>Page not found</div>,
}))
vi.mock('../../../src/pages/FeedPage', () => ({
  default: () => <h1>Feed page stub</h1>,
}))
vi.mock('../../../src/pages/PaperDetailPage', () => ({
  default: () => <h1>Paper detail stub</h1>,
}))
vi.mock('../../../src/pages/OnboardingPage', () => ({
  default: () => <h1>Onboarding stub</h1>,
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

    expect(await screen.findByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
  })

  it('renders PricingPage at /pricing', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/pricing'],
    })

    render(<RouterProvider router={router} />)

    expect(
      await screen.findByRole('heading', { name: /Simple, transparent pricing/ })
    ).toBeInTheDocument()
  })

  it('renders FeedPage at /feed inside the protected layout', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/feed'],
    })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    )

    expect(await screen.findByRole('heading', { name: /Feed page stub/ })).toBeInTheDocument()
  })

  it('redirects old /chat links to the feed', async () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/chat/abc-123'] })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    )

    expect(await screen.findByRole('heading', { name: /Feed page stub/ })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/feed')
  })

  it('renders PaperDetailPage at /papers/:arxivId', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/papers/2401.00001'],
    })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    )

    expect(await screen.findByRole('heading', { name: /Paper detail stub/ })).toBeInTheDocument()
  })

  it('renders OnboardingPage at /onboarding outside the sidebar layout', async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ['/onboarding'],
    })

    render(<RouterProvider router={router} />)

    expect(await screen.findByRole('heading', { name: /Onboarding stub/ })).toBeInTheDocument()
    expect(screen.queryByText('New conversation')).not.toBeInTheDocument()
  })
})

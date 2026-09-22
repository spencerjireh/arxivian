import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { mockAuth } from '../../mocks/clerk'
import type { RouteObject } from 'react-router-dom'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('framer-motion', () => import('../../mocks/framer-motion'))

// Stub protected route to render children directly in tests
vi.mock('@/features/auth/components/ProtectedRoute', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
// No /users/me round trip in route tests
vi.mock('@/lib/api-client', () => ({
  apiGet: vi.fn().mockResolvedValue({}),
  setAuthTokenGetter: vi.fn(),
}))

// Mock lazy-loaded pages with lightweight stubs so the route tests
// verify routing logic only -- page rendering is covered by page-level tests.
vi.mock('@/app/routes/AboutPage', () => ({
  default: () => <h1>Papers you could</h1>,
}))
vi.mock('@/app/routes/PricingPage', () => ({
  default: () => <h1>Simple, transparent pricing</h1>,
}))
vi.mock('@/app/routes/NotFoundPage', () => ({
  default: () => <div>Page not found</div>,
}))
vi.mock('@/app/routes/FeedPage', () => ({
  default: () => <h1>Feed page stub</h1>,
}))
vi.mock('@/app/routes/PaperDetailPage', () => ({
  default: () => <h1>Paper detail stub</h1>,
}))
vi.mock('@/app/routes/OnboardingPage', () => ({
  default: () => <h1>Onboarding stub</h1>,
}))
vi.mock('@/app/routes/LibraryPage', () => ({
  default: () => <h1>Library stub</h1>,
}))

// Eagerly resolve the App module (and all transitive non-mocked imports)
// before any test runs, so the first test doesn't pay the cold-start cost
// that would push React.lazy resolution past findBy* timeouts.
let routes: RouteObject[]
beforeAll(async () => {
  const mod = await import('@/app/router')
  routes = mod.routes
})

beforeEach(() => {
  mockAuth.isSignedIn = false
})

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
  return router
}

describe('App routes', () => {
  it('shows 404 page for unknown paths', async () => {
    renderAt('/nonexistent')
    expect(await screen.findByText('Page not found')).toBeInTheDocument()
  })

  it('renders the feed at / inside the top-nav shell, signed out', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: /Feed page stub/ })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('link', { name: 'Library' })).not.toBeInTheDocument()
  })

  it('redirects the legacy /feed to / keeping the query string', async () => {
    const view = renderAt('/feed?week=2026-08-03')
    expect(await screen.findByRole('heading', { name: /Feed page stub/ })).toBeInTheDocument()
    expect(view.state.location.pathname).toBe('/')
    expect(view.state.location.search).toBe('?week=2026-08-03')
  })

  it('redirects old /chat links to the feed', async () => {
    const view = renderAt('/chat/abc-123')
    expect(await screen.findByRole('heading', { name: /Feed page stub/ })).toBeInTheDocument()
    expect(view.state.location.pathname).toBe('/')
  })

  it('renders AboutPage at /about', async () => {
    renderAt('/about')
    expect(await screen.findByRole('heading', { name: /Papers you could/ })).toBeInTheDocument()
  })

  it('renders PricingPage at /pricing', async () => {
    renderAt('/pricing')
    expect(
      await screen.findByRole('heading', { name: /Simple, transparent pricing/ })
    ).toBeInTheDocument()
  })

  it('renders PaperDetailPage at /papers/:arxivId', async () => {
    renderAt('/papers/2401.00001')
    expect(await screen.findByRole('heading', { name: /Paper detail stub/ })).toBeInTheDocument()
  })

  it('shows the account links in the nav when signed in', async () => {
    mockAuth.isSignedIn = true
    renderAt('/library')
    expect(await screen.findByRole('heading', { name: /Library stub/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Library' })).toHaveAttribute('href', '/library')
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
    expect(screen.queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument()
  })

  it('renders OnboardingPage at /onboarding outside the shell', async () => {
    renderAt('/onboarding')
    expect(await screen.findByRole('heading', { name: /Onboarding stub/ })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument()
  })
})

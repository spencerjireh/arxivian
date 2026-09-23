import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import AuthSession from '@/features/auth/components/AuthSession'
import { useUserStore } from '@/stores/userStore'
import { mockAuth, mockClerk } from '../../../../mocks/clerk'

vi.mock('@clerk/clerk-react', () => import('../../../../mocks/clerk'))

const apiGet = vi.fn()
const setAuthTokenGetter = vi.fn()
vi.mock('@/lib/api-client', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  setAuthTokenGetter: (getter: unknown) => setAuthTokenGetter(getter),
}))

const me = {
  id: 'u',
  email: null,
  first_name: null,
  last_name: null,
  tier: 'free' as const,
  daily_chat_limit: 10,
  chats_used_today: 0,
  onboarded: true,
}

function renderSession(path = '/') {
  const queryClient = new QueryClient()
  const router = createMemoryRouter(
    [
      {
        element: <AuthSession />,
        children: [
          { path: '/', element: <div>public page</div> },
          { path: '/sign-in', element: <div>sign-in page</div> },
        ],
      },
    ],
    { initialEntries: [path] }
  )
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
  return { router, queryClient }
}

beforeEach(() => {
  mockAuth.isSignedIn = false
  mockAuth.isLoaded = true
  apiGet.mockReset().mockResolvedValue(me)
  setAuthTokenGetter.mockClear()
  mockClerk.signOut.mockClear()
  useUserStore.setState({ me: null, loading: false, error: null })
})

describe('AuthSession', () => {
  it('renders the page for an anonymous visitor and never loads /users/me', async () => {
    renderSession()
    expect(await screen.findByText('public page')).toBeInTheDocument()
    expect(apiGet).not.toHaveBeenCalled()
    const getter = setAuthTokenGetter.mock.calls[0][0] as () => Promise<string | null>
    await expect(getter()).resolves.toBeNull()
  })

  it('loads /users/me once and registers the Clerk token getter when signed in', async () => {
    mockAuth.isSignedIn = true
    renderSession()
    expect(await screen.findByText('public page')).toBeInTheDocument()
    await vi.waitFor(() => expect(useUserStore.getState().me).toEqual(me))
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith('/users/me')
    const getter = setAuthTokenGetter.mock.calls[0][0] as () => Promise<string | null>
    await expect(getter()).resolves.toBe('mock-token')
  })

  it('waits for Clerk to load before rendering anything', () => {
    mockAuth.isLoaded = false
    renderSession()
    expect(screen.queryByText('public page')).not.toBeInTheDocument()
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('signs out and goes to /sign-in on a forced auth:signout', async () => {
    mockAuth.isSignedIn = true
    useUserStore.setState({ me })
    const { router: view } = renderSession()
    await screen.findByText('public page')
    fireEvent(window, new CustomEvent('auth:signout'))
    await vi.waitFor(() => expect(mockClerk.signOut).toHaveBeenCalledTimes(1))
    await vi.waitFor(() => expect(view.state.location.pathname).toBe('/sign-in'))
    expect(useUserStore.getState().me).toBeNull()
  })

  it('drops every cached query when a signed-in session ends', async () => {
    mockAuth.isSignedIn = true
    const { router, queryClient } = renderSession()
    await screen.findByText('public page')
    queryClient.setQueryData(['feed', 'list', {}], { items: [{ state: 'saved' }] })
    expect(queryClient.getQueryCache().getAll()).toHaveLength(1)

    mockAuth.isSignedIn = false
    // Clerk flips isSignedIn; the layout re-renders through a navigation to the same route.
    await router.navigate('/')
    await vi.waitFor(() => expect(queryClient.getQueryCache().getAll()).toHaveLength(0))
    expect(useUserStore.getState().me).toBeNull()
  })

  it('keeps the cache for a visitor who was never signed in', async () => {
    const { router, queryClient } = renderSession()
    await screen.findByText('public page')
    queryClient.setQueryData(['feed', 'list', {}], { items: [] })
    await router.navigate('/')
    expect(queryClient.getQueryCache().getAll()).toHaveLength(1)
  })
})

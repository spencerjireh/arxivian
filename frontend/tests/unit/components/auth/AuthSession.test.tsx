import { render, screen, fireEvent } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { mockAuth, mockClerk } from '../../../mocks/clerk'
import AuthSession from '../../../../src/components/auth/AuthSession'
import { useUserStore } from '../../../../src/stores/userStore'

vi.mock('@clerk/clerk-react', () => import('../../../mocks/clerk'))

const apiGet = vi.fn()
const setAuthTokenGetter = vi.fn()
vi.mock('../../../../src/api/client', () => ({
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
  render(<RouterProvider router={router} />)
  return router
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
    const view = renderSession()
    await screen.findByText('public page')
    fireEvent(window, new CustomEvent('auth:signout'))
    await vi.waitFor(() => expect(mockClerk.signOut).toHaveBeenCalledTimes(1))
    await vi.waitFor(() => expect(view.state.location.pathname).toBe('/sign-in'))
    expect(useUserStore.getState().me).toBeNull()
  })
})

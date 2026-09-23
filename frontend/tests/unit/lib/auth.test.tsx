import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { meKeys, useMe, useSession } from '@/lib/auth'
import { mockAuth, mockClerk } from '../../mocks/clerk'
import type { ReactNode } from 'react'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))

const apiGet = vi.fn()
vi.mock('@/lib/api-client', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
}))

const me = {
  id: 'u',
  email: null,
  first_name: null,
  last_name: null,
  tier: 'free' as const,
  daily_chat_limit: 10,
  chats_used_today: 3,
}

function setup() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { queryClient, wrapper }
}

beforeEach(() => {
  mockAuth.isSignedIn = false
  apiGet.mockReset().mockResolvedValue(me)
  mockClerk.signOut.mockClear()
})

describe('useMe', () => {
  it('never fetches for an anonymous visitor', () => {
    const { wrapper } = setup()
    const { result } = renderHook(() => useMe(), { wrapper })
    expect(result.current.data).toBeUndefined()
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('fetches /users/me once for a signed-in visitor', async () => {
    mockAuth.isSignedIn = true
    const { wrapper } = setup()
    const { result } = renderHook(() => useMe(), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual(me))
    expect(apiGet).toHaveBeenCalledTimes(1)
    expect(apiGet).toHaveBeenCalledWith('/users/me')
  })
})

describe('useSession', () => {
  it('exposes the signed-in state, me and the Clerk user', async () => {
    mockAuth.isSignedIn = true
    const { wrapper } = setup()
    const { result } = renderHook(() => useSession(), { wrapper })
    expect(result.current.isLoaded).toBe(true)
    expect(result.current.isSignedIn).toBe(true)
    expect(result.current.user?.fullName).toBe('Test User')
    await waitFor(() => expect(result.current.me).toEqual(me))
  })

  it('masks me and user when signed out, even with a cached record', () => {
    const { queryClient, wrapper } = setup()
    queryClient.setQueryData(meKeys.me(), me)
    const { result } = renderHook(() => useSession(), { wrapper })
    expect(result.current.isSignedIn).toBe(false)
    expect(result.current.me).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('signOut drops the me query before signing out of Clerk', async () => {
    mockAuth.isSignedIn = true
    const { queryClient, wrapper } = setup()
    const { result } = renderHook(() => useSession(), { wrapper })
    await waitFor(() => expect(result.current.me).toEqual(me))
    await act(async () => {
      await result.current.signOut()
    })
    expect(queryClient.getQueryData(meKeys.me())).toBeUndefined()
    expect(mockClerk.signOut).toHaveBeenCalledTimes(1)
  })
})

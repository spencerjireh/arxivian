// Root layout route: registers Clerk's token getter and the 401 handler with lib/api-client.ts,
// prefetches /users/me for a signed-in visitor (never for an anonymous one) and drops the
// query cache when a session ends.
import { useCallback, useEffect, useRef } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth, useClerk } from '@clerk/clerk-react'
import { useQueryClient } from '@tanstack/react-query'
import Spinner from '@/components/ui/Spinner'
import { setAuthTokenGetter, setUnauthorizedHandler } from '@/lib/api-client'
import { meKeys, meQueryOptions } from '@/lib/auth'

/**
 * Sits above every route so a signed-in reader gets a bearer token and `me` on the public
 * pages too. Renders a spinner until Clerk has loaded, which is what guarantees the first
 * feed request of a signed-in reader carries the token (and is cached with their state).
 */
export default function AuthSession() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { signOut } = useClerk()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const wasSignedIn = useRef(false)

  // Forced sign-out from an API 401 on a request that carried a token.
  const handleForceSignOut = useCallback(async () => {
    queryClient.removeQueries({ queryKey: meKeys.all })
    await signOut()
    await navigate('/sign-in')
  }, [queryClient, signOut, navigate])

  // Register synchronously (not in useEffect) so children can make authenticated requests
  // on their first render. Anonymous visitors send no Authorization header.
  setAuthTokenGetter(isSignedIn ? () => getToken().catch(() => null) : () => Promise.resolve(null))
  setUnauthorizedHandler(() => void handleForceSignOut())

  useEffect(() => {
    if (!isLoaded) return
    if (isSignedIn) {
      wasSignedIn.current = true
      void queryClient.prefetchQuery(meQueryOptions(true))
      return
    }
    // Feed items, score details, library and chat threads are cached with the previous
    // user's state; an anonymous view must not serve them.
    if (wasSignedIn.current) {
      wasSignedIn.current = false
      queryClient.clear()
    }
  }, [isLoaded, isSignedIn, queryClient])

  if (!isLoaded) {
    return <Spinner fullScreen />
  }

  return <Outlet />
}

// Root layout route: registers Clerk's token getter with api/client.ts, loads /users/me for a
// signed-in visitor (never for an anonymous one) and handles forced sign-out on a 401.
import { useCallback, useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth, useClerk } from '@clerk/clerk-react'
import { Loader2 } from 'lucide-react'
import { setAuthTokenGetter } from '../../api/client'
import { useUserStore } from '../../stores/userStore'

/**
 * Sits above every route so a signed-in reader gets a bearer token and `me` on the public
 * pages too. Renders a spinner until Clerk has loaded, which is what guarantees the first
 * feed request of a signed-in reader carries the token (and is cached with their state).
 */
export default function AuthSession() {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { signOut } = useClerk()
  const navigate = useNavigate()
  const fetchMe = useUserStore((s) => s.fetchMe)
  const clear = useUserStore((s) => s.clear)

  // Register synchronously (not in useEffect) so children can make authenticated requests
  // on their first render. Anonymous visitors send no Authorization header.
  setAuthTokenGetter(isSignedIn ? () => getToken().catch(() => null) : () => Promise.resolve(null))

  const handleForceSignOut = useCallback(async () => {
    clear()
    await signOut()
    await navigate('/sign-in')
  }, [clear, signOut, navigate])

  useEffect(() => {
    if (!isLoaded) return
    if (isSignedIn) void fetchMe()
    else clear()
  }, [isLoaded, isSignedIn, fetchMe, clear])

  // Forced sign-out from an API 401 on a request that carried a token
  useEffect(() => {
    const onSignOut = () => void handleForceSignOut()
    window.addEventListener('auth:signout', onSignOut)
    return () => window.removeEventListener('auth:signout', onSignOut)
  }, [handleForceSignOut])

  if (!isLoaded) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
      </div>
    )
  }

  return <Outlet />
}

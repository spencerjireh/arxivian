import { useEffect, useCallback } from 'react'
import { useAuth, useClerk } from '@clerk/clerk-react'
import { useNavigate } from 'react-router-dom'
import { setAuthTokenGetter } from '../../api/client'
import { useUserStore } from '../../stores/userStore'

/**
 * Registers the Clerk token getter with the API client and fetches user info.
 * Must be rendered inside ClerkProvider and wraps protected routes.
 *
 * Also listens for 'auth:signout' events dispatched by the API layer on 401
 * responses, triggering a full sign-out + redirect to /sign-in.
 */
export default function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()
  const { signOut } = useClerk()
  const navigate = useNavigate()
  const fetchMe = useUserStore((s) => s.fetchMe)
  const clearUserStore = useUserStore((s) => s.clear)

  // Register token getter synchronously (not in useEffect) so children
  // can make authenticated requests on their first render.
  setAuthTokenGetter(() => getToken().catch(() => null))

  const handleForceSignOut = useCallback(async () => {
    clearUserStore()
    await signOut()
    await navigate('/sign-in')
  }, [clearUserStore, signOut, navigate])

  // Fetch user tier/usage info once on mount
  useEffect(() => {
    void fetchMe()
  }, [fetchMe])

  // Listen for forced sign-out from API 401 responses
  useEffect(() => {
    const onSignOut = () => void handleForceSignOut()
    window.addEventListener('auth:signout', onSignOut)
    return () => window.removeEventListener('auth:signout', onSignOut)
  }, [handleForceSignOut])

  return <>{children}</>
}

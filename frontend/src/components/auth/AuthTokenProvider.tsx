import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { setAuthTokenGetter } from '../../api/client'
import { useUserStore } from '../../stores/userStore'

/**
 * Registers the Clerk token getter with the API client and fetches user info.
 * Must be rendered inside ClerkProvider and wraps protected routes.
 */
export default function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()
  const fetchMe = useUserStore((s) => s.fetchMe)

  // Register token getter synchronously (not in useEffect) so children
  // can make authenticated requests on their first render.
  setAuthTokenGetter(() => getToken().catch(() => null))

  // Fetch user tier/usage info once on mount
  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  return <>{children}</>
}

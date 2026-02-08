import { useAuth } from '@clerk/clerk-react'
import { setAuthTokenGetter } from '../../api/client'

/**
 * Registers the Clerk token getter with the API client.
 * Must be rendered inside ClerkProvider and wraps protected routes.
 */
export default function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()
  setAuthTokenGetter(() => getToken().catch(() => null))
  return <>{children}</>
}

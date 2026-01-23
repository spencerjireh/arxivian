import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { setAuthTokenGetter } from '../../api/client'

/**
 * Registers the Clerk token getter with the API client.
 * Must be rendered inside ClerkProvider and wraps protected routes.
 */
export default function AuthTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()

  useEffect(() => {
    // Register the token getter with the API client
    setAuthTokenGetter(async () => {
      try {
        const token = await getToken()
        return token
      } catch {
        return null
      }
    })
  }, [getToken])

  return <>{children}</>
}

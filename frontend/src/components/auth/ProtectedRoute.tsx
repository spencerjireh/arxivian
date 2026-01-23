import { SignedIn, SignedOut } from '@clerk/clerk-react'
import { Navigate, useLocation } from 'react-router-dom'
import AuthTokenProvider from './AuthTokenProvider'

interface ProtectedRouteProps {
  children: React.ReactNode
}

/**
 * Wraps routes that require authentication.
 * Redirects unauthenticated users to sign-in.
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()

  return (
    <>
      <SignedIn>
        <AuthTokenProvider>{children}</AuthTokenProvider>
      </SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" state={{ from: location }} replace />
      </SignedOut>
    </>
  )
}

// Route wrapper: renders children only when Clerk reports a signed-in user, else redirects to /sign-in.
import { SignedIn, SignedOut } from '@clerk/clerk-react'
import { Navigate, useLocation } from 'react-router-dom'

interface ProtectedRouteProps {
  children: React.ReactNode
}

/**
 * Wraps routes that require authentication. Redirects unauthenticated users to sign-in and
 * remembers where they were (`state.from`) so sign-in can return them there.
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()

  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" state={{ from: location }} replace />
      </SignedOut>
    </>
  )
}

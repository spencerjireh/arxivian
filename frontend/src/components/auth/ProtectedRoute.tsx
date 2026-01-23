import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react'
import AuthTokenProvider from './AuthTokenProvider'

interface ProtectedRouteProps {
  children: React.ReactNode
}

/**
 * Wraps routes that require authentication.
 * Redirects unauthenticated users to sign-in.
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  return (
    <>
      <SignedIn>
        <AuthTokenProvider>{children}</AuthTokenProvider>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  )
}

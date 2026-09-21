// Route wrapper: redirects a signed-in user with me.onboarded === false to /onboarding.
import { Navigate, useLocation } from 'react-router-dom'
import { useUserStore } from '../../stores/userStore'

interface OnboardingGateProps {
  children: React.ReactNode
}

/**
 * Sends a signed-in user with no feed profile to /onboarding. Fails open while `me` is
 * still loading (or failed to load), and never redirects from /onboarding itself.
 */
export default function OnboardingGate({ children }: OnboardingGateProps) {
  const me = useUserStore((s) => s.me)
  const { pathname } = useLocation()

  if (me && me.onboarded === false && !pathname.startsWith('/onboarding')) {
    return <Navigate to="/onboarding" replace state={{ from: pathname }} />
  }
  return <>{children}</>
}

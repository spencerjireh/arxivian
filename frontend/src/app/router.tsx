// The only router: AuthSession above everything, the top-nav Layout for public and signed-in
// pages, ProtectedRoute on the account pages, /feed and /chat/* redirects to /. Route
// components live in ./routes; providers in ./provider.
import { lazy, Suspense, useEffect } from 'react'
import {
  createBrowserRouter,
  matchRoutes,
  Navigate,
  RouterProvider,
  useLocation,
} from 'react-router-dom'
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import Spinner from '../components/ui/Spinner'
import Layout from '../components/layout/Layout'
import AuthSession from '../features/auth/components/AuthSession'
import ProtectedRoute from '../features/auth/components/ProtectedRoute'
import { useSession } from '../lib/auth'
import { setObservabilityContext } from '../lib/observability'
import RouteErrorPage from './routes/RouteErrorPage'
import type { RouteObject } from 'react-router-dom'

const SignInPage = lazy(() => import('./routes/SignInPage'))
const SignUpPage = lazy(() => import('./routes/SignUpPage'))
const AboutPage = lazy(() => import('./routes/AboutPage'))
const PricingPage = lazy(() => import('./routes/PricingPage'))
const LibraryPage = lazy(() => import('./routes/LibraryPage'))
const FeedPage = lazy(() => import('./routes/FeedPage'))
const PaperDetailPage = lazy(() => import('./routes/PaperDetailPage'))
const OnboardingPage = lazy(() => import('./routes/OnboardingPage'))
const SettingsPage = lazy(() => import('./routes/SettingsPage'))
const NotFoundPage = lazy(() => import('./routes/NotFoundPage'))
const PrivacyPage = lazy(() => import('./routes/PrivacyPage'))

function PageFallback() {
  return <Spinner className="flex-1" />
}

function Lazy({
  component: Component,
}: {
  component: React.LazyExoticComponent<() => React.JSX.Element>
}) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Component />
    </Suspense>
  )
}

/** Stamps the matched route template and the signed-in user's id on browser spans. */
function ObservabilityContext() {
  const location = useLocation()
  const { me } = useSession()
  const route = matchRoutes(routes, location)?.at(-1)?.route.path
  useEffect(() => {
    setObservabilityContext({ route, userId: me?.id ?? null })
  }, [route, me?.id])
  return null
}

/** The feed used to live at /feed; old links keep their query string. */
function LegacyFeedRedirect() {
  const { search } = useLocation()
  return <Navigate to={{ pathname: '/', search }} replace />
}

// eslint-disable-next-line react-refresh/only-export-components
export const routes: RouteObject[] = [
  {
    element: (
      <>
        <ObservabilityContext />
        <AuthSession />
      </>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      {
        element: <Layout />,
        children: [
          // Public
          { path: '/', element: <Lazy component={FeedPage} /> },
          { path: '/feed', element: <LegacyFeedRedirect /> },
          // The global chat tab was removed in Phase 3; old links land on the feed.
          { path: '/chat/*', element: <Navigate to="/" replace /> },
          { path: '/papers/:arxivId', element: <Lazy component={PaperDetailPage} /> },
          { path: '/about', element: <Lazy component={AboutPage} /> },
          { path: '/pricing', element: <Lazy component={PricingPage} /> },
          { path: '/privacy', element: <Lazy component={PrivacyPage} /> },
          // Account
          {
            path: '/library',
            element: (
              <ProtectedRoute>
                <Lazy component={LibraryPage} />
              </ProtectedRoute>
            ),
          },
          {
            path: '/settings',
            element: (
              <ProtectedRoute>
                <Lazy component={SettingsPage} />
              </ProtectedRoute>
            ),
          },
        ],
      },
      // Outside the shell
      { path: '/sign-in', element: <Lazy component={SignInPage} /> },
      { path: '/sign-up', element: <Lazy component={SignUpPage} /> },
      { path: '/sso-callback', element: <AuthenticateWithRedirectCallback /> },
      {
        path: '/onboarding',
        element: (
          <ProtectedRoute>
            <Lazy component={OnboardingPage} />
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <Lazy component={NotFoundPage} /> },
    ],
  },
]

const router = createBrowserRouter(routes)

export default function AppRouter() {
  return <RouterProvider router={router} />
}

// The only router: AuthSession above everything, the top-nav Layout for public and signed-in
// pages, ProtectedRoute on the account pages, /feed and /chat/* redirects to /.
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, RouterProvider, useLocation } from 'react-router-dom'
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import { Loader2 } from 'lucide-react'
import Layout from './components/layout/Layout'
import AuthSession from './components/auth/AuthSession'
import ProtectedRoute from './components/auth/ProtectedRoute'
import RouteErrorPage from './pages/RouteErrorPage'
import type { RouteObject } from 'react-router-dom'

const SignInPage = lazy(() => import('./pages/SignInPage'))
const SignUpPage = lazy(() => import('./pages/SignUpPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const PricingPage = lazy(() => import('./pages/PricingPage'))
const LibraryPage = lazy(() => import('./pages/LibraryPage'))
const FeedPage = lazy(() => import('./pages/FeedPage'))
const PaperDetailPage = lazy(() => import('./pages/PaperDetailPage'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const PrivacyPage = lazy(() => import('./pages/PrivacyPage'))

function PageFallback() {
  return (
    <div className="flex flex-1 items-center justify-center py-24">
      <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
    </div>
  )
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

/** The feed used to live at /feed; old links keep their query string. */
function LegacyFeedRedirect() {
  const { search } = useLocation()
  return <Navigate to={{ pathname: '/', search }} replace />
}

// eslint-disable-next-line react-refresh/only-export-components
export const routes: RouteObject[] = [
  {
    element: <AuthSession />,
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

function App() {
  return <RouterProvider router={router} />
}

export default App

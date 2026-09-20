import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import { Loader2 } from 'lucide-react'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import OnboardingGate from './components/auth/OnboardingGate'
import RouteErrorPage from './pages/RouteErrorPage'

const SignInPage = lazy(() => import('./pages/SignInPage'))
const SignUpPage = lazy(() => import('./pages/SignUpPage'))
const LandingPage = lazy(() => import('./pages/LandingPage'))
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
    <div className="flex items-center justify-center h-screen">
      <Loader2 className="w-6 h-6 animate-spin text-stone-300" strokeWidth={1.5} />
    </div>
  )
}

function Lazy({ component: Component }: { component: React.LazyExoticComponent<() => React.JSX.Element> }) {
  return (
    <Suspense fallback={<PageFallback />}>
      <Component />
    </Suspense>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const routes: RouteObject[] = [
  // Public routes
  {
    path: '/',
    element: <Lazy component={LandingPage} />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: '/sign-in',
    element: <Lazy component={SignInPage} />,
  },
  {
    path: '/sign-up',
    element: <Lazy component={SignUpPage} />,
  },
  {
    path: '/pricing',
    element: <Lazy component={PricingPage} />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: '/privacy',
    element: <Lazy component={PrivacyPage} />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: '/sso-callback',
    element: <AuthenticateWithRedirectCallback />,
  },
  // Protected routes
  {
    path: '/onboarding',
    element: (
      <ProtectedRoute>
        <Lazy component={OnboardingPage} />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorPage />,
  },
  {
    element: (
      <ProtectedRoute>
        <OnboardingGate>
          <Layout />
        </OnboardingGate>
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { path: '/feed', element: <Lazy component={FeedPage} /> },
      { path: '/papers/:arxivId', element: <Lazy component={PaperDetailPage} /> },
      // The global chat tab was removed in Phase 3; old links land on the feed.
      { path: '/chat/*', element: <Navigate to="/feed" replace /> },
      { path: '/library', element: <Lazy component={LibraryPage} /> },
      { path: '/settings', element: <Lazy component={SettingsPage} /> },
    ],
  },
  // Catch-all 404
  {
    path: '*',
    element: <Lazy component={NotFoundPage} />,
  },
]

const router = createBrowserRouter(routes)

function App() {
  return <RouterProvider router={router} />
}

export default App

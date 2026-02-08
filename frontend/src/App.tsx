import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import { Loader2 } from 'lucide-react'
import Layout from './components/layout/Layout'
import ChatPage from './pages/ChatPage'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import ProtectedRoute from './components/auth/ProtectedRoute'

const LandingPage = lazy(() => import('./pages/LandingPage'))
const LibraryPage = lazy(() => import('./pages/LibraryPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

function PageFallback() {
  return (
    <div className="flex items-center justify-center h-screen">
      <Loader2 className="w-6 h-6 animate-spin text-stone-300" strokeWidth={1.5} />
    </div>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const routes: RouteObject[] = [
  // Public routes
  {
    path: '/',
    element: (
      <Suspense fallback={<PageFallback />}>
        <LandingPage />
      </Suspense>
    ),
  },
  {
    path: '/sign-in',
    element: <SignInPage />,
  },
  {
    path: '/sign-up',
    element: <SignUpPage />,
  },
  {
    path: '/sso-callback',
    element: <AuthenticateWithRedirectCallback />,
  },
  // Protected routes
  {
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/chat', element: <ChatPage /> },
      { path: '/chat/:sessionId', element: <ChatPage /> },
      {
        path: '/library',
        element: (
          <Suspense fallback={<PageFallback />}>
            <LibraryPage />
          </Suspense>
        ),
      },
      {
        path: '/settings',
        element: (
          <Suspense fallback={<PageFallback />}>
            <SettingsPage />
          </Suspense>
        ),
      },
    ],
  },
  // Catch-all redirect
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]

const router = createBrowserRouter(routes)

function App() {
  return <RouterProvider router={router} />
}

export default App

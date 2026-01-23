import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AuthenticateWithRedirectCallback } from '@clerk/clerk-react'
import Layout from './components/layout/Layout'
import ChatPage from './pages/ChatPage'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import ProtectedRoute from './components/auth/ProtectedRoute'

const router = createBrowserRouter([
  // Auth routes (public)
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
    path: '/',
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <ChatPage /> },
      { path: ':sessionId', element: <ChatPage /> },
    ],
  },
])

function App() {
  return <RouterProvider router={router} />
}

export default App

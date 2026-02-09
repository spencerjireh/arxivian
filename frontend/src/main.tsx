import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
import { toast } from 'sonner'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ui/ErrorBoundary.tsx'
import PageErrorFallback from './components/ui/PageErrorFallback.tsx'
import Toaster from './components/ui/Toaster.tsx'
import { isAuthError, getUserMessage } from './lib/errors.ts'

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY environment variable')
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
    mutations: {
      onError: (error) => {
        if (isAuthError(error)) {
          toast.error('Session expired', {
            description: 'Please sign in again to continue.',
          })
        } else {
          toast.error('Action failed', {
            description: getUserMessage(error),
          })
        }
      },
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary
          fallback={(props) => <PageErrorFallback {...props} />}
        >
          <App />
        </ErrorBoundary>
        <Toaster />
      </QueryClientProvider>
    </ClerkProvider>
  </StrictMode>,
)

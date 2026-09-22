// App-level providers: Clerk, the QueryClient (with the global mutation error toast), the
// root ErrorBoundary and the Toaster. main.tsx wraps the router in this.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClerkProvider } from '@clerk/clerk-react'
import { toast } from 'sonner'
import ErrorBoundary from '../components/ui/ErrorBoundary'
import PageErrorFallback from '../components/ui/PageErrorFallback'
import Toaster from '../components/ui/Toaster'
import { isAuthError, getUserMessage } from '../lib/errors'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: (count, error) => count < 1 && !isAuthError(error),
    },
    mutations: {
      onError: (error) => {
        // Auth errors trigger forced redirect via auth:signout event; skip toast
        if (!isAuthError(error)) {
          toast.error('Action failed', {
            description: getUserMessage(error),
          })
        }
      },
    },
  },
})

interface AppProviderProps {
  clerkPublishableKey: string
  children: React.ReactNode
}

export default function AppProvider({ clerkPublishableKey, children }: AppProviderProps) {
  return (
    <ClerkProvider publishableKey={clerkPublishableKey}>
      <QueryClientProvider client={queryClient}>
        <ErrorBoundary fallback={(props) => <PageErrorFallback {...props} />}>
          {children}
        </ErrorBoundary>
        <Toaster />
      </QueryClientProvider>
    </ClerkProvider>
  )
}

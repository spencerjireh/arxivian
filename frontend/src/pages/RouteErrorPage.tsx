import { useRouteError, isRouteErrorResponse } from 'react-router-dom'
import NotFoundPage from './NotFoundPage'
import PageErrorFallback from '../components/ui/PageErrorFallback'

export default function RouteErrorPage() {
  const routeError = useRouteError()

  if (isRouteErrorResponse(routeError) && routeError.status === 404) {
    return <NotFoundPage />
  }

  const error =
    routeError instanceof Error
      ? routeError
      : new Error(String(routeError ?? 'An unexpected error occurred'))

  return (
    <PageErrorFallback
      error={error}
      resetErrorBoundary={() => { window.location.href = '/' }}
    />
  )
}

// Maps backend error codes (exceptions.py) to user-facing title, message and retry policy.
type ErrorDisplay = 'inline' | 'toast' | 'none'

export interface ErrorTreatment {
  title: string
  body: string | null // null = use backend message
  display: ErrorDisplay
  showRetry: boolean
}

function getCountdownToMidnightUTC(): string {
  const now = new Date()
  const midnight = new Date(now)
  midnight.setUTCDate(midnight.getUTCDate() + 1)
  midnight.setUTCHours(0, 0, 0, 0)
  const diffMs = midnight.getTime() - now.getTime()
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  if (hours > 0) {
    return `Resets in ${hours}h ${minutes}m.`
  }
  return `Resets in ${minutes}m.`
}

const treatments: Record<string, (backendMessage: string) => ErrorTreatment> = {
  USAGE_LIMIT_EXCEEDED: () => ({
    title: 'Daily limit reached',
    body: getCountdownToMidnightUTC(),
    display: 'inline',
    showRetry: false,
  }),
  TIMEOUT: () => ({
    title: 'Response timed out',
    body: 'Try a more specific question.',
    display: 'inline',
    showRetry: true,
  }),
  INTERNAL_ERROR: () => ({
    title: 'Something went wrong',
    body: 'An unexpected error occurred. Please try again.',
    display: 'inline',
    showRetry: true,
  }),
  FORBIDDEN: (msg) => ({
    title: 'Not allowed',
    body: msg,
    display: 'toast',
    showRetry: false,
  }),
  CONNECTION_ERROR: () => ({
    title: 'Connection lost',
    body: 'Check your network and try again.',
    display: 'toast',
    showRetry: false,
  }),
  CANCELLED: () => ({
    title: '',
    body: null,
    display: 'none',
    showRetry: false,
  }),
}

export function getErrorTreatment(code: string, backendMessage: string): ErrorTreatment {
  const factory = treatments[code]
  if (factory) return factory(backendMessage)
  return {
    title: 'Something went wrong',
    body: backendMessage,
    display: 'inline',
    showRetry: true,
  }
}

import { AlertTriangle } from 'lucide-react'
import { getUserMessage } from '../../lib/errors'
import Button from './Button'
import type { FallbackProps } from './ErrorBoundary'

export default function PageErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="paper-grain flex min-h-screen items-center justify-center bg-[var(--color-cream)] p-6">
      <div className="animate-fade-in-up relative z-10 w-full max-w-md rounded-xl border border-stone-200 bg-white p-8 text-center shadow-md">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-error-soft)]">
          <AlertTriangle className="h-5 w-5 text-[var(--color-error)]" strokeWidth={1.5} />
        </div>

        <h1 className="font-display mb-2 text-2xl font-semibold text-stone-900">
          Something went wrong
        </h1>

        <div className="mx-auto mb-4 h-0.5 w-8 bg-[var(--color-accent)]" />

        <p className="mb-6 text-sm leading-relaxed text-stone-500">{getUserMessage(error)}</p>

        <div className="flex items-center justify-center gap-3">
          <Button variant="primary" size="md" onClick={resetErrorBoundary}>
            Try again
          </Button>
          <Button
            variant="secondary"
            size="md"
            onClick={() => {
              window.location.href = '/'
            }}
          >
            Return home
          </Button>
        </div>
      </div>
    </div>
  )
}

import { AlertTriangle } from 'lucide-react'
import { getUserMessage } from '../../lib/errors'
import Button from './Button'
import type { FallbackProps } from './ErrorBoundary'

export default function PageErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div className="min-h-screen bg-[var(--color-cream)] paper-grain flex items-center justify-center p-6">
      <div className="relative z-10 max-w-md w-full bg-white rounded-xl border border-stone-200 shadow-md p-8 text-center animate-fade-in-up">
        <div className="w-12 h-12 rounded-full bg-[var(--color-error-soft)] flex items-center justify-center mx-auto mb-5">
          <AlertTriangle className="w-5 h-5 text-[var(--color-error)]" strokeWidth={1.5} />
        </div>

        <h1 className="font-display text-2xl font-semibold text-stone-900 mb-2">
          Something went wrong
        </h1>

        <div className="w-8 h-0.5 bg-[var(--color-accent)] mx-auto mb-4" />

        <p className="text-sm text-stone-500 leading-relaxed mb-6">
          {getUserMessage(error)}
        </p>

        <div className="flex items-center justify-center gap-3">
          <Button variant="primary" size="md" onClick={resetErrorBoundary}>
            Try again
          </Button>
          <Button variant="secondary" size="md" onClick={() => { window.location.href = '/' }}>
            Return home
          </Button>
        </div>
      </div>
    </div>
  )
}

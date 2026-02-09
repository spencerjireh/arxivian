import { AlertCircle } from 'lucide-react'
import type { FallbackProps } from './ErrorBoundary'

export default function SectionErrorFallback({ resetErrorBoundary }: FallbackProps) {
  return (
    <div className="px-3 py-8 text-center">
      <div className="w-10 h-10 rounded-full bg-[var(--color-error-soft)] flex items-center justify-center mx-auto mb-3">
        <AlertCircle className="w-4 h-4 text-[var(--color-error)]" strokeWidth={1.5} />
      </div>
      <p className="text-sm text-stone-500 mb-2">This section failed to load</p>
      <button
        onClick={resetErrorBoundary}
        className="text-xs text-stone-400 hover:text-stone-600 underline underline-offset-2 transition-colors duration-150"
      >
        Try again
      </button>
    </div>
  )
}

import { AlertCircle, RotateCcw } from 'lucide-react'
import { getErrorTreatment } from '../../lib/errorMapping'
import type { MessageError } from '../../types/api'

interface MessageErrorDisplayProps {
  error: MessageError
  onRetry?: (query: string) => void
  retryQuery?: string
}

export default function MessageErrorDisplay({
  error,
  onRetry,
  retryQuery,
}: MessageErrorDisplayProps) {
  const treatment = getErrorTreatment(error.code, error.message)

  if (treatment.display === 'none') return null

  return (
    <div className="mt-3 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">{treatment.title}</p>
          {treatment.body && <p className="mt-0.5 text-red-600">{treatment.body}</p>}
        </div>
        {treatment.showRetry && onRetry && retryQuery && (
          <button
            type="button"
            onClick={() => onRetry(retryQuery)}
            className="flex flex-shrink-0 items-center gap-1 rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-700 transition-colors hover:bg-red-200 hover:text-red-800"
          >
            <RotateCcw className="h-3 w-3" />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

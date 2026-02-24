import { AlertCircle, RotateCcw } from 'lucide-react'
import type { MessageError } from '../../types/api'
import { getErrorTreatment } from '../../lib/errorMapping'

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
        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="font-medium">{treatment.title}</p>
          {treatment.body && (
            <p className="mt-0.5 text-red-600">{treatment.body}</p>
          )}
        </div>
        {treatment.showRetry && onRetry && retryQuery && (
          <button
            type="button"
            onClick={() => onRetry(retryQuery)}
            className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-700 hover:text-red-800 bg-red-100 hover:bg-red-200 rounded-md transition-colors flex-shrink-0"
          >
            <RotateCcw className="h-3 w-3" />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}

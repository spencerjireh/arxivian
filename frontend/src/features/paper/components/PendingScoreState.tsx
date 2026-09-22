// Paper detail: shown while GET /papers/{id}/score answers 202 (on-demand scoring).
import { Loader2, Clock } from 'lucide-react'
import Button from '@/components/ui/Button'

interface PendingScoreStateProps {
  timedOut: boolean
  onRetry: () => void
}

/** Shown while the backend ingests and scores the paper on demand (202). */
export default function PendingScoreState({ timedOut, onRetry }: PendingScoreStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center" role="status">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100">
        {timedOut ? (
          <Clock className="h-5 w-5 text-stone-400" strokeWidth={1.5} />
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-stone-400" strokeWidth={1.5} />
        )}
      </div>
      {timedOut ? (
        <>
          <p className="text-sm font-medium text-stone-700">Still scoring this paper.</p>
          <p className="mt-1 mb-4 text-sm text-stone-400">
            Full-text scoring can take a few minutes on a busy queue.
          </p>
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Check again
          </Button>
        </>
      ) : (
        <>
          <p className="text-sm font-medium text-stone-700">Ingesting and scoring this paper.</p>
          <p className="mt-1 text-sm text-stone-400">This usually takes a minute or two.</p>
        </>
      )}
    </div>
  )
}

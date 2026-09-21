// Paper detail: the atomic Jev judgments behind a dimension, with probabilities.
import { AlertCircle } from 'lucide-react'
import { formatAnswer, isLowConfidence, judgmentLabel } from '../../lib/scoring'
import type { Judgment } from '../../types/api'

interface JudgmentListProps {
  judgments: Judgment[]
}

/** The atomic Jev answers behind a dimension, with their confidence. */
export default function JudgmentList({ judgments }: JudgmentListProps) {
  if (judgments.length === 0) return null
  return (
    <dl className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1 text-sm">
      {judgments.map((j) => (
        <div key={j.key} className="contents">
          <dt className="text-stone-600">{judgmentLabel(j.key)}</dt>
          <dd className="text-right font-medium text-stone-900">{formatAnswer(j.answer)}</dd>
          <dd className="inline-flex items-center justify-end gap-1 text-right font-mono text-xs text-stone-400">
            {Math.round(j.confidence * 100)}%
            {isLowConfidence(j.confidence) && (
              <AlertCircle
                className="h-3 w-3 text-amber-700"
                strokeWidth={1.5}
                aria-label="Low confidence"
              />
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}

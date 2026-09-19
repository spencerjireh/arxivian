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
          <dd className="text-stone-900 font-medium text-right">{formatAnswer(j.answer)}</dd>
          <dd className="font-mono text-xs text-stone-400 text-right inline-flex items-center gap-1 justify-end">
            {Math.round(j.confidence * 100)}%
            {isLowConfidence(j.confidence) && (
              <AlertCircle className="w-3 h-3 text-amber-700" strokeWidth={1.5} aria-label="Low confidence" />
            )}
          </dd>
        </div>
      ))}
    </dl>
  )
}

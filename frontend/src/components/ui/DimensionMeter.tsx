// Feed card and detail: four-segment meter over the derived sub-scores (backend FeedScores).
import clsx from 'clsx'
import { DIMENSION_LABELS, DIMENSION_ORDER, DIMENSION_SHORT_LABELS } from '@/lib/scoring'
import type { DimensionScores } from '@/types/api'

interface DimensionMeterProps {
  scores: DimensionScores
  size?: 'sm' | 'md'
  className?: string
}

/**
 * One track per dimension in rubric order, filled to the 0-100 sub-score in a single ink
 * colour: no band colours, no band words, no composite. A missing value renders as a hollow
 * dashed track labelled "not available", never as low.
 */
export default function DimensionMeter({ scores, size = 'sm', className }: DimensionMeterProps) {
  const labels = size === 'sm' ? DIMENSION_SHORT_LABELS : DIMENSION_LABELS
  return (
    <ul aria-label="Implementability meter" className={clsx('grid grid-cols-4 gap-2', className)}>
      {DIMENSION_ORDER.map((dimension) => {
        const value = scores[dimension]
        const label = labels[dimension]
        const rounded = value === null ? null : Math.round(value)
        return (
          <li key={dimension} className="min-w-0">
            {rounded === null ? (
              <div
                role="img"
                aria-label={`${label} not available`}
                title={`${label}: not available`}
                data-dimension={dimension}
                data-value="null"
                className="h-1.5 rounded-full border border-dashed border-stone-300"
              />
            ) : (
              <div
                role="meter"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={rounded}
                aria-label={`${label} ${rounded} of 100`}
                title={`${label}: ${rounded}`}
                data-dimension={dimension}
                className="h-1.5 overflow-hidden rounded-full bg-stone-200"
              >
                <div
                  className="h-full rounded-full bg-stone-800"
                  style={{ width: `${rounded}%` }}
                />
              </div>
            )}
            <p
              className={clsx(
                'mt-1 truncate tracking-wider text-stone-500 uppercase',
                size === 'sm' ? 'text-[10px]' : 'text-[11px]'
              )}
            >
              {label}
            </p>
          </li>
        )
      })}
    </ul>
  )
}

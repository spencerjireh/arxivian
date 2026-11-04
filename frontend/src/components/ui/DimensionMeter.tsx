// Feed post and detail: one-track-per-dimension meter over the derived sub-scores (backend FeedScores).
import clsx from 'clsx'
import { DIMENSION_LABELS, DIMENSION_ORDER, DIMENSION_SHORT_LABELS } from '@/lib/scoring'
import type { DimensionScores, ScoreDimension } from '@/types/api'

interface DimensionMeterProps {
  scores: DimensionScores
  /** Which dimensions to draw, in order; the feed omits the data gate (always full there). */
  dimensions?: ScoreDimension[]
  /** Dimensions whose judgment confidence is low: drawn hatched, never hidden. */
  lowConfidence?: ScoreDimension[]
  size?: 'sm' | 'md'
  className?: string
}

const GRID_COLUMNS: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
}

/**
 * One track per dimension, filled to the 0-100 sub-score in a single ink colour: no band
 * colours, no band words, no composite. A low-confidence dimension gets a hatched fill. A
 * missing value renders as a hollow dashed track labelled "not available", never as low.
 */
export default function DimensionMeter({
  scores,
  dimensions = DIMENSION_ORDER,
  lowConfidence = [],
  size = 'sm',
  className,
}: DimensionMeterProps) {
  const labels = size === 'sm' ? DIMENSION_SHORT_LABELS : DIMENSION_LABELS
  return (
    <ul
      aria-label="Implementability meter"
      className={clsx('grid gap-2', GRID_COLUMNS[dimensions.length], className)}
    >
      {dimensions.map((dimension) => {
        const value = scores[dimension]
        const label = labels[dimension]
        const rounded = value === null ? null : Math.round(value)
        const low = lowConfidence.includes(dimension)
        const suffix = low ? ' (low confidence)' : ''
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
                aria-label={`${label} ${rounded} of 100${suffix}`}
                title={`${label}: ${rounded}${suffix}`}
                data-dimension={dimension}
                data-confidence={low ? 'low' : undefined}
                className="h-1.5 overflow-hidden rounded-full bg-stone-200"
              >
                <div
                  className={clsx('h-full rounded-full', low ? 'meter-hatched' : 'bg-stone-800')}
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

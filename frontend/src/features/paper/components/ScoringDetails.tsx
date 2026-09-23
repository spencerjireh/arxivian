// Paper detail: the pipeline internals behind the score (distributions, judgments,
// confidence, rubric version) under one closed-by-default disclosure.
import { AlertCircle } from 'lucide-react'
import Chip from '@/components/ui/Chip'
import { DIMENSION_LABELS, LEVEL_LABELS, isLowConfidence } from '@/lib/scoring'
import { formatDate } from '@/lib/formatting'
import DistributionBar from './DistributionBar'
import JudgmentList from './JudgmentList'
import type { PaperScoreDetail } from '@/types/api'

interface ScoringDetailsProps {
  detail: PaperScoreDetail
}

export default function ScoringDetails({ detail }: ScoringDetailsProps) {
  const lowConfidence = detail.low_confidence.map((d) => DIMENSION_LABELS[d])
  return (
    <details className="rounded-xl border border-stone-200 bg-white">
      <summary className="font-display cursor-pointer px-5 py-4 text-lg text-stone-900 select-none">
        Scoring details
      </summary>
      <div className="space-y-6 border-t border-stone-100 px-5 pt-4 pb-5">
        <p className="text-xs text-stone-400">
          Rubric {detail.rubric_version} · scored {formatDate(detail.scored_at)} · composite{' '}
          {Math.round(detail.scores.composite)} of 100 · every score is derived from the level
          distributions below.
        </p>
        {lowConfidence.length > 0 && (
          <p className="text-sm text-amber-800">
            Low confidence on {lowConfidence.join(', ')}: the judge spread its mass across levels,
            so read the evidence before trusting the band.
          </p>
        )}
        {detail.dimensions.map((dimension) => {
          const labels = LEVEL_LABELS[dimension.dimension]
          const low = isLowConfidence(dimension.confidence)
          return (
            <section key={dimension.dimension} className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h4 className="text-sm font-medium text-stone-900">
                  {DIMENSION_LABELS[dimension.dimension]}
                </h4>
                <span className="font-mono text-sm text-stone-700 tabular-nums">
                  {dimension.score}/100
                </span>
                <span className="font-mono text-xs text-stone-400 tabular-nums">
                  {Math.round(dimension.confidence * 100)}% conf.
                </span>
                {low && (
                  <Chip
                    tone="warning"
                    size="sm"
                    icon={<AlertCircle className="h-3 w-3" strokeWidth={1.5} />}
                  >
                    Low confidence
                  </Chip>
                )}
              </div>
              <div className="flex items-center gap-3">
                <DistributionBar
                  probabilities={dimension.probabilities}
                  level={dimension.level}
                  maxLevel={dimension.max_level}
                  labels={labels}
                  className="flex-1"
                />
                <span className="text-xs whitespace-nowrap text-stone-500">
                  {labels?.[dimension.level] ?? `Level ${dimension.level}`}
                </span>
              </div>
              {dimension.reasoning && (
                <p className="text-xs text-stone-500">{dimension.reasoning}</p>
              )}
              <JudgmentList judgments={dimension.judgments} />
            </section>
          )
        })}
      </div>
    </details>
  )
}

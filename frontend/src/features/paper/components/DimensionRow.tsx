// Paper detail: one rubric dimension, always open: band word, level, plain facts and evidence.
import clsx from 'clsx'
import { DIMENSION_LABELS, LEVEL_LABELS, bandWord, dimensionFacts } from '@/lib/scoring'
import EvidenceList from './EvidenceList'
import type { DimensionDetail } from '@/types/api'

interface DimensionRowProps {
  dimension: DimensionDetail
}

const strongWords = new Set(['Strong', 'Pass'])

/** The public reading of a dimension. Distributions, probabilities and confidence live in
 *  ScoringDetails, not here. */
export default function DimensionRow({ dimension }: DimensionRowProps) {
  const word = bandWord(dimension)
  const level = LEVEL_LABELS[dimension.dimension]?.[dimension.level]
  const facts = dimensionFacts(dimension)
  const headingId = `dimension-${dimension.dimension}`

  return (
    <section
      aria-labelledby={headingId}
      className="rounded-xl border border-stone-200 bg-white px-5 py-4"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 id={headingId} className="font-display text-lg text-stone-900">
          {DIMENSION_LABELS[dimension.dimension]}
        </h3>
        <span
          className={clsx(
            'text-sm font-medium',
            strongWords.has(word) ? 'text-[var(--color-success)]' : 'text-stone-700'
          )}
        >
          {word}
        </span>
        {level && level !== word && <span className="text-sm text-stone-500">{level}</span>}
      </div>
      {facts.length > 0 && <p className="mt-1 text-sm text-stone-600">{facts.join(' · ')}</p>}
      <div className="mt-4">
        <EvidenceList evidence={dimension.evidence} />
      </div>
    </section>
  )
}

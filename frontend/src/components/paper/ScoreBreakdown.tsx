// Paper detail: per-dimension breakdown from GET /papers/{id}/score (backend schemas/papers.py).
import ScoreBadge from '../feed/ScoreBadge'
import VerdictLine from '../feed/VerdictLine'
import SignalChips from '../feed/SignalChips'
import DimensionRow from './DimensionRow'
import EvidenceList from './EvidenceList'
import { DIMENSION_LABELS } from '../../lib/scoring'
import { formatDate } from '../../lib/formatting'
import type { PaperScoreDetail } from '../../types/api'

interface ScoreBreakdownProps {
  detail: PaperScoreDetail
}

/** Composite + verdict on top, then every dimension paired with its quoted evidence. */
export default function ScoreBreakdown({ detail }: ScoreBreakdownProps) {
  const lowConfidence = detail.low_confidence.length > 0
  return (
    <section className="space-y-4" aria-label="Score breakdown">
      <div className="flex items-start gap-4">
        <ScoreBadge
          score={detail.scores.composite}
          size="lg"
          lowConfidence={lowConfidence}
          lowConfidenceTitle={
            lowConfidence
              ? `Low confidence: ${detail.low_confidence.map((d) => DIMENSION_LABELS[d]).join(', ')}`
              : undefined
          }
        />
        <div className="min-w-0 flex-1">
          <VerdictLine verdict={detail.verdict} className="mb-2" />
          <SignalChips signals={detail.signals} size="md" />
        </div>
      </div>
      <p className="text-xs text-stone-400">
        Rubric {detail.rubric_version} · scored {formatDate(detail.scored_at)} · scores are derived
        from the level distributions below; open a dimension for its evidence.
      </p>
      <div className="space-y-3">
        {detail.dimensions.map((dimension, i) => (
          <DimensionRow key={dimension.dimension} dimension={dimension} defaultOpen={i === 0} />
        ))}
      </div>
      {detail.attributes.code_evidence.length > 0 && (
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <h3 className="font-display mb-3 text-lg text-stone-900">Code released by the authors</h3>
          <EvidenceList evidence={detail.attributes.code_evidence} />
        </div>
      )}
    </section>
  )
}

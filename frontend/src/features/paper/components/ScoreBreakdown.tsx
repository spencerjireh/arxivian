// Paper detail: the score as a reader sees it (GET /papers/{id}/score, backend schemas/papers.py).
import AttributeChips from './AttributeChips'
import DimensionRow from './DimensionRow'
import EvidenceList from './EvidenceList'
import ScoreSummary from './ScoreSummary'
import ScoringDetails from './ScoringDetails'
import type { PaperScoreDetail } from '@/types/api'

interface ScoreBreakdownProps {
  detail: PaperScoreDetail
}

/** Headline, meta and meter on top; every dimension open with its band word and evidence;
 *  the pipeline internals folded under Scoring details at the bottom. */
export default function ScoreBreakdown({ detail }: ScoreBreakdownProps) {
  return (
    <section className="space-y-4" aria-label="Score breakdown">
      <ScoreSummary detail={detail} />
      <AttributeChips attributes={detail.attributes} />
      <div className="space-y-3">
        {detail.dimensions.map((dimension) => (
          <DimensionRow key={dimension.dimension} dimension={dimension} />
        ))}
      </div>
      {detail.attributes.code_evidence.length > 0 && (
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <h3 className="font-display mb-3 text-lg text-stone-900">Code released by the authors</h3>
          <EvidenceList evidence={detail.attributes.code_evidence} />
        </div>
      )}
      <ScoringDetails detail={detail} />
    </section>
  )
}

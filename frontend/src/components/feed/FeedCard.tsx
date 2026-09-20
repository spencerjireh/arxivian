import { Link } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import ScoreBadge from './ScoreBadge'
import VerdictLine from './VerdictLine'
import SignalChips from './SignalChips'
import CardActions, { type PendingAction } from './CardActions'
import { DIMENSION_LABELS } from '../../lib/scoring'
import { formatAuthors, formatDate } from '../../utils/formatting'
import type { FeedItem } from '../../types/api'

export interface FeedCardProps {
  item: FeedItem
  onSave: (arxivId: string) => void
  onDismiss: (arxivId: string) => void
  onImplementing: (arxivId: string) => void
  pendingAction?: PendingAction
}

/** One ranked paper. Answers "why should I care?" from the verdict line alone. */
export default function FeedCard({
  item,
  onSave,
  onDismiss,
  onImplementing,
  pendingAction = null,
}: FeedCardProps) {
  const { paper, scores, verdict, signals, low_confidence, state } = item
  const id = paper.arxiv_id
  const lowConfidence = low_confidence.length > 0
  const lowConfidenceTitle = lowConfidence
    ? `Low confidence: ${low_confidence.map((d) => DIMENSION_LABELS[d]).join(', ')}`
    : undefined

  return (
    <article
      className="rounded-xl border border-stone-200 bg-white p-5 transition-colors hover:border-stone-300"
      data-testid={`feed-card-${id}`}
    >
      <div className="mb-2 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            to={`/papers/${encodeURIComponent(id)}`}
            className="font-display line-clamp-2 text-lg leading-snug font-semibold text-stone-900 hover:underline"
          >
            {paper.title}
          </Link>
          <p className="mt-1 truncate text-sm text-stone-500">
            {formatAuthors(paper.authors)}
            {paper.categories[0] && (
              <>
                <span className="mx-1.5 text-stone-300">|</span>
                <span className="font-mono text-xs">{paper.categories[0]}</span>
              </>
            )}
            <span className="mx-1.5 text-stone-300">|</span>
            {formatDate(paper.published_date)}
          </p>
        </div>
        <ScoreBadge
          score={scores.composite}
          lowConfidence={lowConfidence}
          lowConfidenceTitle={lowConfidenceTitle}
          className="shrink-0"
        />
      </div>

      <VerdictLine verdict={verdict} className="mb-3" />

      <SignalChips signals={signals} />

      <div className="mt-3 flex items-center justify-between border-t border-stone-100 pt-3">
        <CardActions
          state={state}
          onSave={() => onSave(id)}
          onDismiss={() => onDismiss(id)}
          onImplementing={() => onImplementing(id)}
          pending={pendingAction}
        />
        <a
          href={paper.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs text-stone-500 transition-colors hover:text-stone-700"
        >
          PDF
          <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
        </a>
      </div>
    </article>
  )
}

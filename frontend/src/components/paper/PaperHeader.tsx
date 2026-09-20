import { Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import CardActions, { type PendingAction } from '../feed/CardActions'
import { formatDate } from '../../utils/formatting'
import type { FeedPaper, PaperState } from '../../types/api'

interface PaperHeaderProps {
  paper: FeedPaper
  state: PaperState | null
  onSave: () => void
  onDismiss: () => void
  onImplementing: () => void
  pending?: PendingAction
}

export default function PaperHeader({
  paper,
  state,
  onSave,
  onDismiss,
  onImplementing,
  pending = null,
}: PaperHeaderProps) {
  const absUrl = `https://arxiv.org/abs/${paper.arxiv_id}`
  return (
    <header className="space-y-3">
      <Link
        to="/feed"
        className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800"
      >
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
        Back to feed
      </Link>
      <h1 className="font-display text-3xl leading-tight font-semibold text-stone-900">
        {paper.title}
      </h1>
      <p className="text-sm text-stone-600">{paper.authors.join(', ')}</p>
      <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
        <span className="rounded bg-stone-100 px-2 py-0.5 font-mono">{paper.arxiv_id}</span>
        {paper.categories.map((cat) => (
          <span key={cat} className="rounded-full bg-stone-100 px-2 py-0.5 text-stone-600">
            {cat}
          </span>
        ))}
        <span>{formatDate(paper.published_date)}</span>
        <a
          href={absUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 hover:text-stone-800"
        >
          abs <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
        </a>
        <a
          href={paper.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 hover:text-stone-800"
        >
          PDF <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
        </a>
      </div>
      <CardActions
        state={state}
        onSave={onSave}
        onDismiss={onDismiss}
        onImplementing={onImplementing}
        pending={pending}
        size="md"
      />
    </header>
  )
}

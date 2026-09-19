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

export default function PaperHeader({ paper, state, onSave, onDismiss, onImplementing, pending = null }: PaperHeaderProps) {
  const absUrl = `https://arxiv.org/abs/${paper.arxiv_id}`
  return (
    <header className="space-y-3">
      <Link to="/feed" className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800">
        <ArrowLeft className="w-4 h-4" strokeWidth={1.5} />
        Back to feed
      </Link>
      <h1 className="font-display text-3xl font-semibold text-stone-900 leading-tight">{paper.title}</h1>
      <p className="text-sm text-stone-600">{paper.authors.join(', ')}</p>
      <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
        <span className="font-mono bg-stone-100 px-2 py-0.5 rounded">{paper.arxiv_id}</span>
        {paper.categories.map((cat) => (
          <span key={cat} className="px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full">{cat}</span>
        ))}
        <span>{formatDate(paper.published_date)}</span>
        <a href={absUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-stone-800">
          abs <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
        </a>
        <a href={paper.pdf_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-stone-800">
          PDF <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
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

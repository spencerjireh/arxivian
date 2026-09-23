// Paper detail: title, authors, date, categories, arXiv link and lifecycle actions.
import { Link } from 'react-router-dom'
import { ArrowLeft, Bookmark, ExternalLink } from 'lucide-react'
import SignInLink from '@/components/ui/SignInLink'
import { formatDate } from '@/lib/formatting'
import CardActions from './CardActions'
import type { FeedPaper, PaperState } from '@/types/api'

interface PaperHeaderProps {
  paper: FeedPaper
  signedIn: boolean
  state: PaperState | null
}

export default function PaperHeader({ paper, signedIn, state }: PaperHeaderProps) {
  const absUrl = `https://arxiv.org/abs/${paper.arxiv_id}`
  return (
    <header className="space-y-3">
      <Link
        to="/"
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
      {signedIn ? (
        <CardActions arxivId={paper.arxiv_id} state={state} offerImplementing size="md" />
      ) : (
        <SignInLink variant="button" leftIcon={<Bookmark className="h-4 w-4" strokeWidth={1.5} />}>
          Save
        </SignInLink>
      )}
    </header>
  )
}

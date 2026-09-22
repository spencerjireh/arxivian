// Paper detail: an unscored paper for an anonymous reader (the 202 metadata) with a sign-in prompt.
import { ExternalLink, LogIn } from 'lucide-react'
import SignInLink from '../auth/SignInLink'
import { formatDate } from '../../lib/formatting'
import type { PaperMetadata } from '../../types/api'

interface PaperPreviewProps {
  paper: PaperMetadata
}

export default function PaperPreview({ paper }: PaperPreviewProps) {
  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
      <header className="space-y-3">
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
            href={paper.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 hover:text-stone-800"
          >
            PDF <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
          </a>
        </div>
      </header>
      <p className="text-sm leading-relaxed text-stone-600">{paper.abstract}</p>
      <aside
        aria-label="Not scored yet"
        className="flex flex-wrap items-center gap-3 rounded-xl border border-stone-200 bg-white px-5 py-4"
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-stone-900">This paper is not scored yet.</p>
          <p className="text-sm text-stone-500">
            Sign in to have it ingested and scored on demand; it takes a minute or two.
          </p>
        </div>
        <SignInLink variant="button" leftIcon={<LogIn className="h-4 w-4" strokeWidth={1.5} />}>
          Sign in to score this paper
        </SignInLink>
      </aside>
    </div>
  )
}

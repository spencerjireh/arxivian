// Feed card: one ranked paper from GET /feed (backend schemas/feed.py::FeedItem).
import { Link } from 'react-router-dom'
import { Bookmark, ExternalLink, Zap } from 'lucide-react'
import Chip from '@/components/ui/Chip'
import DimensionMeter from '@/components/ui/DimensionMeter'
import SignInLink from '@/components/ui/SignInLink'
import CardActions from '@/features/paper/components/CardActions'
import { formatAuthors, formatDate } from '@/lib/formatting'
import type { FeedItem } from '@/types/api'

export interface FeedCardProps {
  item: FeedItem
  /** Anonymous readers get a Save that opens sign-in instead of the lifecycle actions. */
  signedIn: boolean
  /** Library cards offer Mark as Implementing / Mark as shipped; feed cards do not. */
  offerImplementing?: boolean
}

/** One ranked paper: headline, meta line and the dimension meter answer "why should I care?"
 *  from the card alone. A card without a current score (library only) shows the paper and
 *  its actions. */
export default function FeedCard({ item, signedIn, offerImplementing = false }: FeedCardProps) {
  const { paper, scores, headline, meta, compute_match, state } = item
  const id = paper.arxiv_id

  return (
    <article
      className="rounded-xl border border-stone-200 bg-white p-5 transition-colors hover:border-stone-300"
      data-testid={`feed-card-${id}`}
    >
      <div className="mb-3">
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

      {scores ? (
        <>
          <p className="font-display text-lg leading-snug text-stone-900">
            {headline ?? 'Method paper'}
          </p>
          {(meta.length > 0 || compute_match === true) && (
            <p className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-stone-500">
              {meta.length > 0 && <span>{meta.join(' · ')}</span>}
              {compute_match === true && (
                <Chip tone="accent" icon={<Zap className="h-3 w-3" strokeWidth={1.5} />}>
                  Fits your compute
                </Chip>
              )}
            </p>
          )}
          <DimensionMeter scores={scores} size="sm" className="mt-4" />
        </>
      ) : (
        <p className="text-sm text-stone-400">Not scored yet</p>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-stone-100 pt-3">
        {signedIn ? (
          <CardActions arxivId={id} state={state} offerImplementing={offerImplementing} />
        ) : (
          <SignInLink
            variant="button"
            leftIcon={<Bookmark className="h-4 w-4" strokeWidth={1.5} />}
          >
            Save
          </SignInLink>
        )}
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

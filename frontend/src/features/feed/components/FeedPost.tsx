// Feed and Library: one paper as a collapsible timeline post (backend schemas/feed.py::FeedItem).
import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { Bookmark, ChevronDown, Code2, ExternalLink, Zap } from 'lucide-react'
import Button from '@/components/ui/Button'
import Chip from '@/components/ui/Chip'
import { AnimatedCollapse } from '@/components/ui/AnimatedCollapse'
import DimensionMeter from '@/components/ui/DimensionMeter'
import SignInLink from '@/components/ui/SignInLink'
import CardActions from '@/features/paper/components/CardActions'
import { formatAuthors, formatDate } from '@/lib/formatting'
import { LEVEL_LABELS } from '@/lib/scoring'
import type { FeedItem, ScoreDimension } from '@/types/api'

export interface FeedPostProps {
  item: FeedItem
  /** Anonymous readers get a Save that opens sign-in instead of the lifecycle actions. */
  signedIn: boolean
  /** Library posts offer Mark as Implementing / Mark as shipped; feed posts do not. */
  offerImplementing?: boolean
  /** Library opens every post so its actions are visible without a click. */
  defaultExpanded?: boolean
}

/** The data gate is always full on the feed (only passing papers enter a digest). */
const FEED_DIMENSIONS: ScoreDimension[] = ['method_clarity', 'resource_feasibility']

/** Clicks on these inside the post do their own thing and must not toggle it. */
const INTERACTIVE = 'a, button, input, select, textarea, label, form'

/**
 * Collapsed: category and date, the title, two lines of the abstract, the chips that apply
 * and two meters. Expanded: the whole abstract, the authors, the actions and the links.
 * The chevron is the keyboard control; the body toggles on click.
 */
export default function FeedPost({
  item,
  signedIn,
  offerImplementing = false,
  defaultExpanded = false,
}: FeedPostProps) {
  const { paper, scores, compute_match, compute_tier, code_released, keyword_match, state } = item
  const id = paper.arxiv_id
  const [expanded, setExpanded] = useState(defaultExpanded)
  const titleId = useId()
  const bodyId = useId()
  const tierLabel =
    compute_tier === null ? undefined : LEVEL_LABELS.resource_feasibility[compute_tier]
  const toggle = () => setExpanded((value) => !value)

  const onBodyClick = (e: React.MouseEvent<HTMLElement>) => {
    if ((e.target as HTMLElement).closest(INTERACTIVE)) return
    if (window.getSelection()?.isCollapsed === false) return
    toggle()
  }

  return (
    <article
      aria-labelledby={titleId}
      data-testid={`feed-post-${id}`}
      onClick={onBodyClick}
      className="cursor-pointer px-4 py-4 transition-colors hover:bg-white sm:px-5"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_9rem] sm:gap-x-6">
        <div className="min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="text-xs text-stone-500">
              {paper.categories[0] && (
                <>
                  <span className="font-mono">{paper.categories[0]}</span>
                  <span className="mx-1.5 text-stone-300">|</span>
                </>
              )}
              {formatDate(paper.published_date)}
            </p>
            <Button
              variant="icon"
              size="sm"
              aria-expanded={expanded}
              aria-controls={bodyId}
              aria-label={expanded ? 'Collapse' : 'Expand'}
              onClick={toggle}
              className="-mt-1.5 -mr-1.5"
            >
              <ChevronDown
                className={clsx('h-4 w-4 transition-transform', expanded && 'rotate-180')}
                strokeWidth={1.5}
              />
            </Button>
          </div>
          <h2
            id={titleId}
            className="font-display text-lg leading-snug font-semibold text-stone-900"
          >
            <Link to={`/papers/${encodeURIComponent(id)}`} className="hover:underline">
              {paper.title}
            </Link>
          </h2>
          <p className={clsx('mt-1 text-sm text-stone-600', !expanded && 'line-clamp-2')}>
            {paper.abstract}
          </p>
          {(tierLabel || code_released === true || compute_match === true || keyword_match) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {tierLabel && <Chip>{tierLabel}</Chip>}
              {code_released === true && (
                <Chip tone="success" icon={<Code2 className="h-3 w-3" strokeWidth={1.5} />}>
                  Code
                </Chip>
              )}
              {compute_match === true && (
                <Chip tone="accent" icon={<Zap className="h-3 w-3" strokeWidth={1.5} />}>
                  Fits your compute
                </Chip>
              )}
              {keyword_match && <Chip tone="info">Keyword match</Chip>}
            </div>
          )}
        </div>
        {scores ? (
          <DimensionMeter
            scores={scores}
            dimensions={FEED_DIMENSIONS}
            lowConfidence={item.low_confidence}
            size="sm"
            className="sm:pt-6"
          />
        ) : (
          <p className="text-sm text-stone-400 sm:pt-6">Not scored yet</p>
        )}
      </div>

      <div id={bodyId}>
        <AnimatedCollapse isOpen={expanded}>
          <div className="mt-3 space-y-3 border-t border-stone-200/70 pt-3">
            <p className="text-sm text-stone-500">{formatAuthors(paper.authors)}</p>
            <div className="flex flex-wrap items-center justify-between gap-2">
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
              <span className="flex gap-3 text-xs text-stone-500">
                <a
                  href={paper.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 transition-colors hover:text-stone-700"
                >
                  PDF
                  <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
                </a>
                <a
                  href={`https://arxiv.org/abs/${id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 transition-colors hover:text-stone-700"
                >
                  arXiv
                  <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
                </a>
              </span>
            </div>
          </div>
        </AnimatedCollapse>
      </div>
    </article>
  )
}

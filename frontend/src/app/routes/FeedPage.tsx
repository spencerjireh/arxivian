// / route (public): the week as a timeline. One request loads the digest week; sort, search
// and filters run in the browser (features/feed/lib/feedView.ts) and live in the URL.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertCircle, Newspaper, SearchX } from 'lucide-react'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import StatusBlock from '@/components/ui/StatusBlock'
import { useFeedWeek } from '@/features/feed/api/get-feed'
import FeedList from '@/features/feed/components/FeedList'
import FeedToolbar from '@/features/feed/components/FeedToolbar'
import OnboardingPrompt from '@/features/feed/components/OnboardingPrompt'
import { feedParamsFromSearch, formatWeek } from '@/features/feed/lib/feedParams'
import {
  applyView,
  countViewFilters,
  feedViewFromSearch,
  writeFeedView,
  type FeedView,
} from '@/features/feed/lib/feedView'
import { useSession } from '@/lib/auth'
import { getUserMessage } from '@/lib/errors'
import type { AvailableWeek, FeedItem } from '@/types/api'

/** Typing filters at once; the URL catches up after this pause. */
const SEARCH_URL_DEBOUNCE_MS = 150

const EMPTY_ITEMS: FeedItem[] = []
const NO_WEEKS: AvailableWeek[] = []

function paperCount(n: number): string {
  return `${n} paper${n === 1 ? '' : 's'}`
}

export default function FeedPage() {
  const { isSignedIn: signedIn, me } = useSession()
  const [search, setSearchParams] = useSearchParams()
  // Dismissals are per-user state: an anonymous reader's URL cannot ask for them.
  const params = useMemo(() => {
    const parsed = feedParamsFromSearch(search)
    if (!signedIn) delete parsed.include_dismissed
    return parsed
  }, [search, signedIn])
  const view = useMemo(() => feedViewFromSearch(search), [search])
  const profileCategories = me?.preferences?.feed_profile?.categories

  const { data, isLoading, isPlaceholderData, error } = useFeedWeek(params)

  // The search draft filters immediately; the URL write is debounced. When the URL changes
  // underneath (Back, a pasted link), the draft follows it.
  const [query, setQuery] = useState(view.q)
  const [syncedQuery, setSyncedQuery] = useState(view.q)
  if (view.q !== syncedQuery) {
    setSyncedQuery(view.q)
    if (view.q !== query.trim()) setQuery(view.q)
  }
  useEffect(() => {
    if (query.trim() === view.q) return
    const timer = setTimeout(
      () => setSearchParams((prev) => writeFeedView(prev, { q: query }), { replace: true }),
      SEARCH_URL_DEBOUNCE_MS
    )
    return () => clearTimeout(timer)
  }, [query, view.q, setSearchParams])

  // `items.length` is the week unless it beat the router's cap (576 papers on 2026-10-26
  // after a triage re-run), in which case `total` says so and the header admits it.
  const loaded = data?.items ?? EMPTY_ITEMS
  const truncated = data !== undefined && data.total > loaded.length
  const weekCount = truncated
    ? `top ${loaded.length} of ${paperCount(data.total)}`
    : paperCount(loaded.length)
  const liveView = useMemo(() => ({ ...view, q: query }), [view, query])
  const shown = useMemo(() => applyView(loaded, liveView), [loaded, liveView])
  const filterCount = countViewFilters(view) + (params.include_dismissed ? 1 : 0)
  // A view change remounts the list, so only a dismissal animates out.
  const viewKey = [view.sort, query, view.categories.join(','), view.tier ?? '', view.code].join(
    '|'
  )

  // TanStack keeps the last successful data next to an error, so the selector survives a
  // transient failure without extra state.
  const knownWeeks = data?.available_weeks ?? NO_WEEKS
  const sortedWeeks = useMemo(
    () => [...knownWeeks].sort((a, b) => (a.week_start < b.week_start ? 1 : -1)),
    [knownWeeks]
  )
  const currentWeek = data?.week_start ?? params.week ?? sortedWeeks[0]?.week_start
  const weekIndex = sortedWeeks.findIndex((w) => w.week_start === currentWeek)
  const previousWeek = weekIndex >= 0 ? sortedWeeks[weekIndex + 1] : undefined
  const categories = useMemo(
    () =>
      [...new Set([...(profileCategories ?? []), ...(data?.categories_available ?? [])])].sort(),
    [profileCategories, data]
  )

  const changeView = useCallback(
    (patch: Partial<FeedView>) =>
      setSearchParams((prev) => writeFeedView(prev, patch), { replace: true }),
    [setSearchParams]
  )
  const changeDismissed = useCallback(
    (next: boolean) =>
      setSearchParams(
        (prev) => {
          const out = new URLSearchParams(prev)
          if (next) out.set('dismissed', '1')
          else out.delete('dismissed')
          return out
        },
        { replace: true }
      ),
    [setSearchParams]
  )
  /** Drop the filters (and the dismissed toggle); the search and sort stay unless `all`. */
  const clearFilters = useCallback(
    (all = false) => {
      if (all) setQuery('')
      setSearchParams(
        (prev) => {
          const out = writeFeedView(prev, {
            categories: [],
            tier: null,
            code: false,
            ...(all ? { q: '', sort: 'ranked' as const } : {}),
          })
          out.delete('dismissed')
          return out
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )
  const selectWeek = useCallback(
    (week: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('week', week)
        return next
      })
      window.scrollTo({ top: 0 })
    },
    [setSearchParams]
  )

  const previousWeekSearch = useMemo(() => {
    if (!previousWeek) return null
    const next = new URLSearchParams(search)
    next.set('week', previousWeek.week_start)
    return `?${next.toString()}`
  }, [previousWeek, search])

  return (
    <div className="mx-auto w-full max-w-3xl px-6 pt-10 pb-16">
      <header className="pb-4">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-stone-900">
            {data?.week_start ? `Week of ${formatWeek(data.week_start)}` : 'Weekly issue'}
          </h1>
          {data && (
            <span className="font-mono text-sm text-stone-400">
              {shown.length === loaded.length
                ? weekCount
                : `${shown.length} of ${paperCount(loaded.length)}`}
            </span>
          )}
        </div>
        <p className="mt-2 max-w-xl text-sm text-stone-500">
          New arXiv papers scored for how implementable they are: how clearly the method is
          specified, what it takes to run, and whether the data is public.
        </p>
      </header>

      {data && currentWeek && (
        <FeedToolbar
          view={view}
          onViewChange={changeView}
          query={query}
          onQueryChange={setQuery}
          weeks={knownWeeks}
          week={currentWeek}
          onWeekChange={selectWeek}
          categories={categories}
          showDismissed={signedIn}
          includeDismissed={Boolean(params.include_dismissed)}
          onDismissedChange={changeDismissed}
          onClear={() => clearFilters()}
          filterCount={filterCount}
        />
      )}

      <div className="pt-6">
        <OnboardingPrompt />
      </div>

      <div className={isPlaceholderData ? 'opacity-60' : undefined}>
        {isLoading ? (
          <Spinner />
        ) : error ? (
          <StatusBlock icon={AlertCircle} tone="error" title={getUserMessage(error)} />
        ) : loaded.length === 0 ? (
          <StatusBlock
            icon={Newspaper}
            title="No papers scored for this week yet"
            hint="The weekly digest is built after the scoring run completes"
          />
        ) : shown.length === 0 ? (
          <StatusBlock
            icon={SearchX}
            title="No papers match"
            hint="Loosen the filters or clear the search"
          >
            <Button
              variant="secondary"
              size="sm"
              className="mt-4"
              onClick={() => clearFilters(true)}
            >
              Show the whole week
            </Button>
          </StatusBlock>
        ) : (
          <>
            <FeedList key={viewKey} items={shown} signedIn={signedIn} />
            {previousWeek && previousWeekSearch && (
              <p className="pt-8 text-center text-sm text-stone-500">
                <Link
                  to={{ search: previousWeekSearch }}
                  onClick={() => window.scrollTo({ top: 0 })}
                  className="text-stone-700 underline decoration-stone-300 underline-offset-4 hover:text-stone-900"
                >
                  Week of {formatWeek(previousWeek.week_start)} (
                  {paperCount(previousWeek.paper_count)})
                </Link>
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

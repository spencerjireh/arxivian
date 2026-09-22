// / route (public): the weekly issue with the week selector, filters and, when signed in,
// the profile prompt. Each card owns its lifecycle actions.
import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AlertCircle, Newspaper } from 'lucide-react'
import Button from '@/components/ui/Button'
import Spinner from '@/components/ui/Spinner'
import StatusBlock from '@/components/ui/StatusBlock'
import { useInfiniteFeed } from '@/features/feed/api/get-feed'
import FeedFilterBar, { type FeedFilters } from '@/features/feed/components/FeedFilterBar'
import FeedList from '@/features/feed/components/FeedList'
import OnboardingPrompt from '@/features/feed/components/OnboardingPrompt'
import WeekSelector from '@/features/feed/components/WeekSelector'
import { feedParamsFromSearch, formatWeek } from '@/features/feed/lib/feedParams'
import { useSession } from '@/lib/auth'
import { getUserMessage } from '@/lib/errors'
import type { AvailableWeek, FeedItem } from '@/types/api'

export default function FeedPage() {
  const { isSignedIn: signedIn, me } = useSession()
  const [search, setSearchParams] = useSearchParams()
  // Dismissals are per-user state: an anonymous reader's URL cannot ask for them.
  const params = useMemo(() => {
    const parsed = feedParamsFromSearch(search)
    if (!signedIn) delete parsed.include_dismissed
    return parsed
  }, [search, signedIn])
  const profileCategories = me?.preferences?.feed_profile?.categories

  const {
    data,
    isLoading,
    isPlaceholderData,
    error,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useInfiniteFeed(params)

  const items: FeedItem[] = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data])
  const first = data?.pages[0]
  const total = first?.total ?? 0
  const hasFilters = Boolean(params.category || params.min_score !== undefined)

  // TanStack keeps the last successful data next to an error, so the selector survives a
  // transient failure without extra state.
  const knownWeeks: AvailableWeek[] = first?.available_weeks ?? []
  const categories = useMemo(
    () =>
      [...new Set([...(profileCategories ?? []), ...(first?.categories_available ?? [])])].sort(),
    [profileCategories, first]
  )

  const selectWeek = useCallback(
    (week: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('week', week)
        return next
      })
    },
    [setSearchParams]
  )
  const changeFilters = useCallback(
    (next: FeedFilters) => {
      setSearchParams(
        (prev) => {
          const out = new URLSearchParams(prev)
          if ('category' in next) {
            if (next.category) out.set('category', next.category)
            else out.delete('category')
          }
          if ('minScore' in next) {
            if (next.minScore !== undefined) out.set('min_score', String(next.minScore))
            else out.delete('min_score')
          }
          if ('includeDismissed' in next) {
            if (next.includeDismissed) out.set('dismissed', '1')
            else out.delete('dismissed')
          }
          return out
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <header className="border-b border-stone-300 pb-6">
        <p className="font-display text-sm tracking-[0.2em] text-stone-500 uppercase">Arxivian</p>
        <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <h1 className="font-display text-4xl font-semibold tracking-tight text-stone-900">
            {first?.week_start ? `Week of ${formatWeek(first.week_start)}` : 'Weekly issue'}
          </h1>
          {first && (
            <span className="font-mono text-sm text-stone-400">
              {total} paper{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <p className="mt-2 max-w-xl text-sm text-stone-500">
          New arXiv papers scored for how implementable they are: how clearly the method is
          specified, what it takes to run, whether the data is public, and how much demand there is.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3 py-5">
        {knownWeeks.length > 0 && (
          <WeekSelector
            weeks={knownWeeks}
            value={first?.week_start ?? params.week ?? knownWeeks[0].week_start}
            onChange={selectWeek}
          />
        )}
        <FeedFilterBar
          categories={categories}
          category={params.category}
          minScore={params.min_score}
          includeDismissed={Boolean(params.include_dismissed)}
          showDismissed={signedIn}
          onChange={changeFilters}
        />
      </div>

      <OnboardingPrompt />

      <div className={isPlaceholderData ? 'opacity-60' : undefined}>
        {isLoading ? (
          <Spinner />
        ) : error ? (
          <StatusBlock icon={AlertCircle} tone="error" title={getUserMessage(error)} />
        ) : items.length === 0 ? (
          <StatusBlock
            icon={Newspaper}
            title={
              hasFilters ? 'No papers match these filters' : 'No papers scored for this week yet'
            }
            hint={
              hasFilters
                ? 'Loosen the filters to see more of the digest'
                : 'The weekly digest is built after the scoring run completes'
            }
          />
        ) : (
          <>
            <FeedList items={items} signedIn={signedIn} />
            {hasNextPage && (
              <div className="flex justify-center pt-6">
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => fetchNextPage()}
                  isLoading={isFetchingNextPage}
                >
                  Load more
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

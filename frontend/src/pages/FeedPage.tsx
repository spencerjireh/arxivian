// / route (public): the weekly issue with the week selector, filters and, when signed in,
// the lifecycle actions and the profile prompt.
import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { AlertCircle, Loader2, Newspaper } from 'lucide-react'
import { useInfiniteFeed } from '../api/feed'
import { useClearPaperState, useSetPaperState } from '../api/paperStates'
import FeedList from '../components/feed/FeedList'
import FeedFilterBar, { type FeedFilters } from '../components/feed/FeedFilterBar'
import OnboardingPrompt from '../components/feed/OnboardingPrompt'
import WeekSelector from '../components/feed/WeekSelector'
import Button from '../components/ui/Button'
import { getUserMessage } from '../lib/errors'
import { feedParamsFromSearch, formatWeek } from '../lib/feedParams'
import { useUserStore } from '../stores/userStore'
import type { PendingAction } from '../components/feed/CardActions'
import type { AvailableWeek, FeedItem } from '../types/api'

export default function FeedPage() {
  const { isSignedIn } = useAuth()
  const signedIn = Boolean(isSignedIn)
  const [search, setSearchParams] = useSearchParams()
  // Dismissals are per-user state: an anonymous reader's URL cannot ask for them.
  const params = useMemo(() => {
    const parsed = feedParamsFromSearch(search)
    if (!signedIn) delete parsed.include_dismissed
    return parsed
  }, [search, signedIn])
  const profileCategories = useUserStore((s) => s.me?.preferences?.feed_profile?.categories)

  const {
    data,
    isLoading,
    isPlaceholderData,
    error,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useInfiniteFeed(params)
  const setState = useSetPaperState()
  const clearState = useClearPaperState()
  const [pending, setPending] = useState<{ arxivId: string; action: PendingAction } | null>(null)

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
  const stateOf = useCallback(
    (arxivId: string) => items.find((i) => i.paper.arxiv_id === arxivId)?.state ?? null,
    [items]
  )

  const run = useCallback((arxivId: string, action: PendingAction, fn: () => Promise<unknown>) => {
    setPending({ arxivId, action })
    void fn().finally(() => setPending((p) => (p?.arxivId === arxivId ? null : p)))
  }, [])

  const onSave = useCallback(
    (arxivId: string) => {
      if (stateOf(arxivId)?.state === 'saved') {
        run(arxivId, 'clear', () => clearState.mutateAsync({ arxivId }).catch(() => undefined))
      } else {
        run(arxivId, 'saved', () =>
          setState.mutateAsync({ arxivId, body: { state: 'saved' } }).catch(() => undefined)
        )
      }
    },
    [stateOf, run, clearState, setState]
  )

  const onDismiss = useCallback(
    (arxivId: string) =>
      run(arxivId, 'dismissed', () =>
        setState.mutateAsync({ arxivId, body: { state: 'dismissed' } }).catch(() => undefined)
      ),
    [run, setState]
  )

  const pendingFor = useCallback(
    (arxivId: string): PendingAction => (pending?.arxivId === arxivId ? pending.action : null),
    [pending]
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
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-error-soft)]">
              <AlertCircle className="h-5 w-5 text-[var(--color-error)]" strokeWidth={1.5} />
            </div>
            <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100">
              <Newspaper className="h-5 w-5 text-stone-400" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-stone-700">
              {hasFilters ? 'No papers match these filters' : 'No papers scored for this week yet'}
            </p>
            <p className="mt-1 text-sm text-stone-400">
              {hasFilters
                ? 'Loosen the filters to see more of the digest'
                : 'The weekly digest is built after the scoring run completes'}
            </p>
          </div>
        ) : (
          <>
            <FeedList
              items={items}
              signedIn={signedIn}
              onSave={onSave}
              onDismiss={onDismiss}
              pendingFor={pendingFor}
            />
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

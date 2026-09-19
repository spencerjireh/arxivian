import { useCallback, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AlertCircle, Loader2, Newspaper } from 'lucide-react'
import { useInfiniteFeed } from '../api/feed'
import { useClearPaperState, useSetPaperState } from '../api/paperState'
import FeedList from '../components/feed/FeedList'
import type { PendingAction } from '../components/feed/CardActions'
import Button from '../components/ui/Button'
import { getUserMessage } from '../lib/errors'
import { feedParamsFromSearch, formatWeek } from '../lib/feedParams'
import type { FeedItem } from '../types/api'

export default function FeedPage() {
  const [search] = useSearchParams()
  const params = useMemo(() => feedParamsFromSearch(search), [search])

  const { data, isLoading, isPlaceholderData, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useInfiniteFeed(params)
  const setState = useSetPaperState()
  const clearState = useClearPaperState()
  const [pending, setPending] = useState<{ arxivId: string; action: PendingAction } | null>(null)

  const items: FeedItem[] = useMemo(() => data?.pages.flatMap((p) => p.items) ?? [], [data])
  const first = data?.pages[0]
  const total = first?.total ?? 0
  const hasFilters = Boolean(params.category || params.min_score !== undefined)
  const stateOf = useCallback(
    (arxivId: string) => items.find((i) => i.paper.arxiv_id === arxivId)?.state ?? null,
    [items],
  )

  const run = useCallback(
    (arxivId: string, action: PendingAction, fn: () => Promise<unknown>) => {
      setPending({ arxivId, action })
      fn().finally(() => setPending((p) => (p?.arxivId === arxivId ? null : p)))
    },
    [],
  )

  const onSave = useCallback(
    (arxivId: string) => {
      if (stateOf(arxivId)?.state === 'saved') {
        run(arxivId, 'clear', () => clearState.mutateAsync({ arxivId }).catch(() => undefined))
      } else {
        run(arxivId, 'saved', () =>
          setState.mutateAsync({ arxivId, body: { state: 'saved' } }).catch(() => undefined),
        )
      }
    },
    [stateOf, run, clearState, setState],
  )

  const onDismiss = useCallback(
    (arxivId: string) =>
      run(arxivId, 'dismissed', () =>
        setState.mutateAsync({ arxivId, body: { state: 'dismissed' } }).catch(() => undefined),
      ),
    [run, setState],
  )

  const onImplementing = useCallback(
    (arxivId: string) => {
      const next = stateOf(arxivId)?.state === 'implementing' ? 'saved' : 'implementing'
      run(arxivId, next, () =>
        setState.mutateAsync({ arxivId, body: { state: next } }).catch(() => undefined),
      )
    },
    [stateOf, run, setState],
  )

  const pendingFor = useCallback(
    (arxivId: string): PendingAction => (pending?.arxivId === arxivId ? pending.action : null),
    [pending],
  )

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-2xl font-semibold text-stone-900">Feed</h1>
          {first?.week_start && (
            <span className="text-sm text-stone-500">Week of {formatWeek(first.week_start)}</span>
          )}
          {first && (
            <span className="text-sm text-stone-400 font-mono">
              {total} paper{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      <div className={`flex-1 overflow-y-auto px-6 pb-6 ${isPlaceholderData ? 'opacity-60' : ''}`}>
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-12 h-12 rounded-full bg-[var(--color-error-soft)] flex items-center justify-center mb-3">
              <AlertCircle className="w-5 h-5 text-[var(--color-error)]" strokeWidth={1.5} />
            </div>
            <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mb-3">
              <Newspaper className="w-5 h-5 text-stone-400" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-stone-700">
              {hasFilters ? 'No papers match these filters' : 'No papers scored for this week yet'}
            </p>
            <p className="text-sm text-stone-400 mt-1">
              {hasFilters
                ? 'Loosen the filters to see more of the digest'
                : 'The weekly digest is built after the scoring run completes'}
            </p>
          </div>
        ) : (
          <>
            <FeedList
              items={items}
              onSave={onSave}
              onDismiss={onDismiss}
              onImplementing={onImplementing}
              pendingFor={pendingFor}
            />
            {hasNextPage && (
              <div className="max-w-3xl flex justify-center pt-6">
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

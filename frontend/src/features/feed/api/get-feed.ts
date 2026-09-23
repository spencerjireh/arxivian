// Feed REST API + TanStack Query hooks (Phase 2, ARX-10)

import { useInfiniteQuery, keepPreviousData } from '@tanstack/react-query'
import { apiGet } from '@/lib/api-client'
import { feedKeys, normalizeFeedParams } from '@/lib/query-keys'
import type { FeedParams, FeedResponse } from '@/types/api'

const FEED_PAGE_SIZE = 20

export function buildFeedQuery(params: FeedParams, offset: number): string {
  const p = normalizeFeedParams(params)
  const searchParams = new URLSearchParams()
  searchParams.set('offset', String(offset))
  searchParams.set('limit', String(p.limit ?? FEED_PAGE_SIZE))
  if (p.week) searchParams.set('week', p.week)
  if (p.category) searchParams.set('category', p.category)
  if (p.min_score !== undefined) searchParams.set('min_score', String(p.min_score))
  if (p.include_dismissed) searchParams.set('include_dismissed', 'true')
  return `/feed?${searchParams.toString()}`
}

async function fetchFeed(params: FeedParams, offset: number): Promise<FeedResponse> {
  return apiGet<FeedResponse>(buildFeedQuery(params, offset))
}

export function useInfiniteFeed(params: FeedParams) {
  return useInfiniteQuery({
    queryKey: feedKeys.list(params),
    queryFn: ({ pageParam = 0 }) => fetchFeed(params, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((n, page) => n + page.items.length, 0)
      return loaded < lastPage.total ? loaded : undefined
    },
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  })
}

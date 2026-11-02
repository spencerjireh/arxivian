// GET /feed: one digest week in a single request (useFeedWeek) under the feed query key
// (backend routers/feed.py). Sort, search and filters run in the browser over the result.

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api-client'
import { feedKeys, normalizeFeedParams } from '@/lib/query-keys'
import type { FeedParams, FeedResponse } from '@/types/api'

/** The router's cap; a digest week has a few hundred papers at most, so one page is the week. */
const FEED_WEEK_LIMIT = 500

export function buildFeedQuery(params: FeedParams): string {
  const p = normalizeFeedParams(params)
  const searchParams = new URLSearchParams()
  searchParams.set('limit', String(FEED_WEEK_LIMIT))
  if (p.week) searchParams.set('week', p.week)
  if (p.include_dismissed) searchParams.set('include_dismissed', 'true')
  return `/feed?${searchParams.toString()}`
}

export function useFeedWeek(params: FeedParams) {
  return useQuery({
    queryKey: feedKeys.list(params),
    queryFn: () => apiGet<FeedResponse>(buildFeedQuery(params)),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  })
}

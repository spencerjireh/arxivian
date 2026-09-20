// Feed REST API + TanStack Query hooks (Phase 2, SPE-274)

import { useInfiniteQuery, keepPreviousData } from '@tanstack/react-query'
import { apiGet } from './client'
import type { FeedParams, FeedResponse } from '../types/api'

const FEED_PAGE_SIZE = 20

/** Drop undefined / empty values so equal filters produce equal query keys. */
export function normalizeFeedParams(params: FeedParams): FeedParams {
  const out: FeedParams = {}
  if (params.week) out.week = params.week
  if (params.category) out.category = params.category
  if (params.min_score !== undefined) out.min_score = params.min_score
  if (params.include_dismissed) out.include_dismissed = true
  if (params.limit !== undefined) out.limit = params.limit
  return out
}

export const feedKeys = {
  all: ['feed'] as const,
  lists: () => [...feedKeys.all, 'list'] as const,
  list: (params: FeedParams) => [...feedKeys.lists(), normalizeFeedParams(params)] as const,
}

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

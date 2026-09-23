// TanStack Query key factories for every server-cache domain. Shared so a feature can
// invalidate another feature's cache (a paper state change touches the feed, the score
// detail and the library) without importing across features.
import type { FeedParams } from '../types/api'

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

export const libraryKeys = {
  all: ['library'] as const,
}

export const scoreKeys = {
  all: ['scores'] as const,
  details: () => [...scoreKeys.all, 'detail'] as const,
  detail: (arxivId: string) => [...scoreKeys.details(), arxivId] as const,
}

export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  paperList: (arxivId: string) => [...conversationKeys.lists(), 'paper', arxivId] as const,
  details: () => [...conversationKeys.all, 'detail'] as const,
  detail: (sessionId: string) => [...conversationKeys.details(), sessionId] as const,
}

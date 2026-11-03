// TanStack Query key factories for every server-cache domain. Shared so a feature can
// invalidate another feature's cache (a paper state change touches the feed, the score
// detail and the library) without importing across features.
import type { FeedParams } from '../types/api'

/**
 * Drop undefined / empty values so equal params produce equal query keys. Only the server
 * params belong here: the client-side view (sort, search, category, tier, code) runs over
 * the loaded week, and a key that carried it would refetch per keystroke and leave
 * paper-state.ts patching stale copies.
 */
export function normalizeFeedParams(params: FeedParams): FeedParams {
  const out: FeedParams = {}
  if (params.week) out.week = params.week
  if (params.include_dismissed) out.include_dismissed = true
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

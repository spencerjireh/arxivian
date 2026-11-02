// Client-side feed view (sort, search, category / tier / code filters): the URL codec and the
// pure applyView() that runs over a loaded digest week. Nothing here reaches the server.
import type { FeedItem } from '@/types/api'

export type FeedSort = 'ranked' | 'newest'
export type ComputeTierFilter = 'laptop' | 'consumer' | 'datacenter'

export interface FeedView {
  sort: FeedSort
  q: string
  categories: string[]
  tier: ComputeTierFilter | null
  code: boolean
}

export const EMPTY_VIEW: FeedView = {
  sort: 'ranked',
  q: '',
  categories: [],
  tier: null,
  code: false,
}

/**
 * "Runs on at most": a paper qualifies when its `compute_tier` level is at least this. The
 * levels index `LEVEL_LABELS.resource_feasibility` (0 cluster .. 4 laptop).
 */
export const TIER_MIN_LEVEL: Record<ComputeTierFilter, number> = {
  laptop: 4,
  consumer: 3,
  datacenter: 2,
}

/** Filter options in UI order, cheapest hardware first. */
export const TIER_OPTIONS: ComputeTierFilter[] = ['laptop', 'consumer', 'datacenter']

function isTier(value: string | null): value is ComputeTierFilter {
  return value !== null && value in TIER_MIN_LEVEL
}

/** Read the view from the URL; anything invalid falls back to the default. */
export function feedViewFromSearch(search: URLSearchParams): FeedView {
  const categories = search
    .getAll('category')
    .flatMap((value) => value.split(','))
    .map((value) => value.trim())
    .filter(Boolean)
  const tier = search.get('tier')
  return {
    sort: search.get('sort') === 'newest' ? 'newest' : 'ranked',
    q: search.get('q') ?? '',
    categories: [...new Set(categories)],
    tier: isTier(tier) ? tier : null,
    code: search.get('code') === '1',
  }
}

/**
 * Copy `prev` with only the keys in `patch` rewritten; a default value deletes its param.
 * The server params (`week`, `dismissed`) are never touched.
 */
export function writeFeedView(prev: URLSearchParams, patch: Partial<FeedView>): URLSearchParams {
  const next = new URLSearchParams(prev)
  if (patch.sort !== undefined) {
    if (patch.sort === 'newest') next.set('sort', 'newest')
    else next.delete('sort')
  }
  if (patch.q !== undefined) {
    const q = patch.q.trim()
    if (q) next.set('q', q)
    else next.delete('q')
  }
  if (patch.categories !== undefined) {
    next.delete('category')
    for (const category of patch.categories) next.append('category', category)
  }
  if (patch.tier !== undefined) {
    if (patch.tier) next.set('tier', patch.tier)
    else next.delete('tier')
  }
  if (patch.code !== undefined) {
    if (patch.code) next.set('code', '1')
    else next.delete('code')
  }
  return next
}

/** How many filters narrow the week: categories, tier, code. Search and sort are not filters. */
export function countViewFilters(view: FeedView): number {
  return (view.categories.length > 0 ? 1 : 0) + (view.tier ? 1 : 0) + (view.code ? 1 : 0)
}

/** Search, filter and sort a loaded week. `ranked` keeps the server's order. */
export function applyView(items: FeedItem[], view: FeedView): FeedItem[] {
  const needle = view.q.trim().toLowerCase()
  const categories = new Set(view.categories)
  const minLevel = view.tier ? TIER_MIN_LEVEL[view.tier] : null

  let out = items.filter((item) => {
    if (needle) {
      const haystack = `${item.paper.title}\n${item.paper.abstract}`.toLowerCase()
      if (!haystack.includes(needle)) return false
    }
    if (categories.size > 0 && !item.paper.categories.some((c) => categories.has(c))) return false
    if (minLevel !== null && (item.compute_tier === null || item.compute_tier < minLevel)) {
      return false
    }
    if (view.code && item.code_released !== true) return false
    return true
  })

  if (view.sort === 'newest') {
    out = out
      .map((item, index) => ({ item, index, time: Date.parse(item.paper.published_date) }))
      .sort((a, b) => b.time - a.time || a.index - b.index)
      .map(({ item }) => item)
  }
  return out
}

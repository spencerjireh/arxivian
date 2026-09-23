// GET /feed query params <-> URL search params, plus week label formatting.
import type { FeedParams } from '@/types/api'

const WEEK_RE = /^\d{4}-\d{2}-\d{2}$/

/** Read the feed filters from the URL; invalid values are ignored. */
export function feedParamsFromSearch(search: URLSearchParams): FeedParams {
  const params: FeedParams = {}
  const week = search.get('week')
  if (week && WEEK_RE.test(week)) params.week = week
  const category = search.get('category')
  if (category) params.category = category
  const minScore = search.get('min_score')
  if (minScore !== null) {
    const n = Number(minScore)
    if (Number.isInteger(n) && n >= 0 && n <= 100) params.min_score = n
  }
  if (search.get('dismissed') === '1') params.include_dismissed = true
  return params
}

/** "Mar 3" from an ISO date, without timezone shifting. */
export function formatWeek(weekStart: string): string {
  const [y, m, d] = weekStart.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Server-side GET /feed params <-> URL (week, dismissed) plus week label formatting. The
// client-side view params (sort, q, category, tier, code) live in feedView.ts.
import type { FeedParams } from '@/types/api'

const WEEK_RE = /^\d{4}-\d{2}-\d{2}$/

/** Read the server params from the URL; invalid values are ignored. */
export function feedParamsFromSearch(search: URLSearchParams): FeedParams {
  const params: FeedParams = {}
  const week = search.get('week')
  if (week && WEEK_RE.test(week)) params.week = week
  if (search.get('dismissed') === '1') params.include_dismissed = true
  return params
}

/** "Mar 3" from an ISO date, without timezone shifting. */
export function formatWeek(weekStart: string): string {
  const [y, m, d] = weekStart.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

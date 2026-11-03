import { feedParamsFromSearch, formatWeek } from '@/features/feed/lib/feedParams'

describe('feedParamsFromSearch', () => {
  it('reads the server params', () => {
    expect(feedParamsFromSearch(new URLSearchParams('week=2026-08-03&dismissed=1'))).toEqual({
      week: '2026-08-03',
      include_dismissed: true,
    })
  })

  it('ignores invalid values and the client-side view params', () => {
    expect(
      feedParamsFromSearch(
        new URLSearchParams('week=foo&dismissed=0&min_score=40&category=cs.LG&q=x&sort=newest')
      )
    ).toEqual({})
  })
})

describe('formatWeek', () => {
  it('formats without timezone shifting', () => {
    expect(formatWeek('2026-08-03')).toBe('Aug 3')
  })
})

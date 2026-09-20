import { bandFor, isLowConfidence } from '../../../src/lib/scoring'
import { feedParamsFromSearch, formatWeek } from '../../../src/lib/feedParams'
import { matchesNav } from '../../../src/lib/nav'

describe('scoring helpers', () => {
  it('bands at 40 and 70', () => {
    expect(bandFor(39)).toBe('LOW')
    expect(bandFor(40)).toBe('MED')
    expect(bandFor(69)).toBe('MED')
    expect(bandFor(70)).toBe('HIGH')
  })

  it('low confidence below 0.5', () => {
    expect(isLowConfidence(0.49)).toBe(true)
    expect(isLowConfidence(0.5)).toBe(false)
  })
})

describe('feedParamsFromSearch', () => {
  it('reads valid params and ignores invalid ones', () => {
    const params = feedParamsFromSearch(
      new URLSearchParams('week=2026-08-03&category=cs.LG&min_score=40&dismissed=1')
    )
    expect(params).toEqual({
      week: '2026-08-03',
      category: 'cs.LG',
      min_score: 40,
      include_dismissed: true,
    })
    expect(feedParamsFromSearch(new URLSearchParams('week=foo&min_score=101&dismissed=0'))).toEqual(
      {}
    )
  })

  it('formats the week without timezone drift', () => {
    expect(formatWeek('2026-08-03')).toBe('Aug 3')
  })
})

describe('matchesNav', () => {
  it('treats paper detail as the feed', () => {
    expect(matchesNav('/feed', '/papers/2401.00001')).toBe(true)
    expect(matchesNav('/feed', '/feed?week=x')).toBe(true)
    expect(matchesNav('/library', '/library')).toBe(true)
    expect(matchesNav('/library', '/feed')).toBe(false)
  })
})

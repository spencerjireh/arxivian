import { bandFor, isLowConfidence } from '../../../src/lib/scoring'
import { feedParamsFromSearch, formatWeek } from '../../../src/lib/feedParams'
import { matchesNav, returnPathFrom } from '../../../src/lib/nav'

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
  it('treats paper detail and the legacy /feed as the feed', () => {
    expect(matchesNav('/', '/')).toBe(true)
    expect(matchesNav('/', '/papers/2401.00001')).toBe(true)
    expect(matchesNav('/', '/feed?week=x')).toBe(true)
    expect(matchesNav('/', '/about')).toBe(false)
    expect(matchesNav('/library', '/library')).toBe(true)
    expect(matchesNav('/library', '/')).toBe(false)
  })
})

describe('returnPathFrom', () => {
  it('accepts a path string or a router Location', () => {
    expect(returnPathFrom({ from: '/papers/2401.00001' })).toBe('/papers/2401.00001')
    expect(returnPathFrom({ from: { pathname: '/', search: '?week=2026-08-03' } })).toBe(
      '/?week=2026-08-03'
    )
  })

  it('falls back to the feed for anything that is not a same-origin path', () => {
    expect(returnPathFrom(undefined)).toBe('/')
    expect(returnPathFrom(null)).toBe('/')
    expect(returnPathFrom({})).toBe('/')
    expect(returnPathFrom({ from: '//evil.example' })).toBe('/')
    expect(returnPathFrom({ from: 'https://evil.example/x' })).toBe('/')
    expect(returnPathFrom({ from: '/\\evil.example' })).toBe('/')
    expect(returnPathFrom({ from: '/papers\\..\\x' })).toBe('/')
    expect(returnPathFrom({ from: { pathname: 42 } })).toBe('/')
  })
})

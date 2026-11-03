import {
  EMPTY_VIEW,
  applyView,
  countViewFilters,
  feedViewFromSearch,
  writeFeedView,
  type FeedView,
} from '@/features/feed/lib/feedView'
import { makeFeedItem } from '../../../../fixtures/feed'
import type { FeedItem } from '@/types/api'

function item(
  arxivId: string,
  overrides: Partial<FeedItem> = {},
  paper: Partial<FeedItem['paper']> = {}
): FeedItem {
  const base = makeFeedItem()
  return makeFeedItem({ ...overrides, paper: { ...base.paper, arxiv_id: arxivId, ...paper } })
}

function ids(items: FeedItem[]): string[] {
  return items.map((i) => i.paper.arxiv_id)
}

function view(overrides: Partial<FeedView> = {}): FeedView {
  return { ...EMPTY_VIEW, ...overrides }
}

describe('feedViewFromSearch', () => {
  it('reads the defaults from an empty search', () => {
    expect(feedViewFromSearch(new URLSearchParams(''))).toEqual(EMPTY_VIEW)
  })

  it('reads every param and ignores invalid values', () => {
    expect(
      feedViewFromSearch(
        new URLSearchParams('sort=newest&q=attention&category=cs.LG&tier=consumer&code=1')
      )
    ).toEqual({
      sort: 'newest',
      q: 'attention',
      categories: ['cs.LG'],
      tier: 'consumer',
      code: true,
    })
    expect(feedViewFromSearch(new URLSearchParams('sort=foo&tier=mainframe&code=0'))).toEqual(
      EMPTY_VIEW
    )
  })

  it('accepts repeated and comma-joined categories, deduped and trimmed', () => {
    expect(
      feedViewFromSearch(new URLSearchParams('category=cs.LG,cs.CV&category=cs.LG&category= ,'))
        .categories
    ).toEqual(['cs.LG', 'cs.CV'])
  })
})

describe('writeFeedView', () => {
  it('sets only the patched keys and leaves the server params alone', () => {
    const prev = new URLSearchParams('week=2026-08-03&dismissed=1&q=old')
    const next = writeFeedView(prev, { sort: 'newest', tier: 'laptop', code: true })
    expect(next.toString()).toBe('week=2026-08-03&dismissed=1&q=old&sort=newest&tier=laptop&code=1')
    expect(prev.toString()).toBe('week=2026-08-03&dismissed=1&q=old')
  })

  it('deletes a param set back to its default', () => {
    const prev = new URLSearchParams('sort=newest&q=x&category=cs.LG&tier=laptop&code=1')
    const next = writeFeedView(prev, {
      sort: 'ranked',
      q: '  ',
      categories: [],
      tier: null,
      code: false,
    })
    expect(next.toString()).toBe('')
  })

  it('writes categories as repeated params and trims the query', () => {
    const next = writeFeedView(new URLSearchParams(''), {
      categories: ['cs.LG', 'cs.CV'],
      q: ' attention ',
    })
    expect(next.toString()).toBe('q=attention&category=cs.LG&category=cs.CV')
  })
})

describe('countViewFilters', () => {
  it('counts categories, tier and code but not search or sort', () => {
    expect(countViewFilters(view({ q: 'x', sort: 'newest' }))).toBe(0)
    expect(countViewFilters(view({ categories: ['cs.LG'] }))).toBe(1)
    expect(countViewFilters(view({ categories: ['cs.LG'], tier: 'laptop', code: true }))).toBe(3)
  })
})

describe('applyView', () => {
  const items = [
    item('a', { compute_tier: 4, code_released: true }, { published_date: '2024-01-10T00:00:00Z' }),
    item(
      'b',
      { compute_tier: 3, code_released: false },
      { title: 'Sparse Mixtures', categories: ['cs.LG'], published_date: '2024-01-12T00:00:00Z' }
    ),
    item(
      'c',
      { compute_tier: null, code_released: null },
      { abstract: 'A note on attention sinks.', published_date: '2024-01-12T00:00:00Z' }
    ),
    item('d', { compute_tier: 1, code_released: true }, { published_date: '2024-01-01T00:00:00Z' }),
  ]

  it('keeps the server order when nothing is set', () => {
    expect(applyView(items, view())).toEqual(items)
  })

  it('searches title and abstract, case-insensitive and trimmed', () => {
    expect(ids(applyView(items, view({ q: ' ATTENTION ' })))).toEqual(['a', 'c', 'd'])
    expect(ids(applyView(items, view({ q: 'sparse' })))).toEqual(['b'])
    expect(ids(applyView(items, view({ q: 'sinks' })))).toEqual(['c'])
  })

  it('keeps a paper in any of the chosen categories, over all of its categories', () => {
    expect(ids(applyView(items, view({ categories: ['cs.LG'] })))).toEqual(['b'])
    expect(ids(applyView(items, view({ categories: ['cs.AI'] })))).toEqual(['a', 'c', 'd'])
    expect(ids(applyView(items, view({ categories: ['cs.AI', 'cs.LG'] })))).toEqual([
      'a',
      'b',
      'c',
      'd',
    ])
  })

  it('tier is "runs on at most" and an unknown tier never qualifies', () => {
    expect(ids(applyView(items, view({ tier: 'laptop' })))).toEqual(['a'])
    expect(ids(applyView(items, view({ tier: 'consumer' })))).toEqual(['a', 'b'])
    expect(ids(applyView(items, view({ tier: 'datacenter' })))).toEqual(['a', 'b'])
  })

  it('code keeps only a true value, never null or false', () => {
    expect(ids(applyView(items, view({ code: true })))).toEqual(['a', 'd'])
  })

  it('newest sorts by published date and keeps the server order within a day', () => {
    expect(ids(applyView(items, view({ sort: 'newest' })))).toEqual(['b', 'c', 'a', 'd'])
  })

  it('composes filters, search and sort', () => {
    expect(ids(applyView(items, view({ sort: 'newest', q: 'attention', code: true })))).toEqual([
      'a',
      'd',
    ])
  })
})

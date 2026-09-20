import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import {
  buildFeedQuery,
  feedKeys,
  normalizeFeedParams,
  useInfiniteFeed,
} from '../../../src/api/feed'
import { makeFeedItem, makeFeedResponse } from '../../fixtures/feed'
import type { ReactNode } from 'react'

const apiGet = vi.fn()
vi.mock('../../../src/api/client', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
}))

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('feed api', () => {
  it('normalizes params so equal filters share a key', () => {
    expect(normalizeFeedParams({ week: undefined, category: '', min_score: undefined })).toEqual({})
    expect(feedKeys.list({ category: 'cs.LG' })).toEqual(
      feedKeys.list({ category: 'cs.LG', week: '' })
    )
    expect(normalizeFeedParams({ include_dismissed: false })).toEqual({})
  })

  it('builds the query string', () => {
    expect(buildFeedQuery({}, 0)).toBe('/feed?offset=0&limit=20')
    expect(
      buildFeedQuery(
        { week: '2026-08-03', category: 'cs.LG', min_score: 40, include_dismissed: true },
        20
      )
    ).toBe(
      '/feed?offset=20&limit=20&week=2026-08-03&category=cs.LG&min_score=40&include_dismissed=true'
    )
  })

  it('fetches the first page and stops when everything is loaded', async () => {
    apiGet.mockResolvedValueOnce(makeFeedResponse([makeFeedItem()], { total: 1 }))
    const { result } = renderHook(() => useInfiniteFeed({}), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(apiGet).toHaveBeenCalledWith('/feed?offset=0&limit=20')
    expect(result.current.hasNextPage).toBe(false)
  })

  it('offers a next page while fewer items than total are loaded', async () => {
    apiGet.mockResolvedValueOnce(makeFeedResponse([makeFeedItem()], { total: 5 }))
    const { result } = renderHook(() => useInfiniteFeed({}), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.hasNextPage).toBe(true)
  })
})

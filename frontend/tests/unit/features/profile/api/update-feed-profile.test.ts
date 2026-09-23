import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { useUpdateFeedProfile } from '@/features/profile/api/update-feed-profile'
import { meKeys } from '@/lib/auth'
import { feedKeys } from '@/lib/query-keys'
import type { ReactNode } from 'react'

const apiPatch = vi.fn()
vi.mock('@/lib/api-client', () => ({
  apiPatch: (...args: unknown[]) => apiPatch(...args),
  apiGet: vi.fn(),
}))

const me = {
  id: 'u',
  email: null,
  first_name: null,
  last_name: null,
  tier: 'free' as const,
  daily_chat_limit: null,
  chats_used_today: 0,
  preferences: {
    feed_profile: { categories: ['cs.LG'], compute_profile: 'laptop' as const, keywords: [] },
  },
  onboarded: false,
}

describe('useUpdateFeedProfile', () => {
  it('patches, writes me into the cache as onboarded, and invalidates the feed', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children)
    apiPatch.mockResolvedValueOnce(me)

    const { result } = renderHook(() => useUpdateFeedProfile(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        categories: ['cs.LG'],
        compute_profile: 'laptop',
        keywords: [],
      })
    })

    expect(apiPatch).toHaveBeenCalledWith('/users/me/preferences', {
      categories: ['cs.LG'],
      compute_profile: 'laptop',
      keywords: [],
    })
    await waitFor(() =>
      expect(queryClient.getQueryData(meKeys.me())).toEqual({ ...me, onboarded: true })
    )
    expect(invalidate).toHaveBeenCalledWith({ queryKey: feedKeys.lists() })
  })
})

import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import { feedKeys, libraryKeys, scoreKeys } from '@/lib/query-keys'
import { applyStateToCaches, useSetPaperState } from '@/features/paper/api/paper-state'
import { makeFeedItem, makeLibraryResponse, makeFeedResponse } from '../../../../fixtures/feed'
import type { ReactNode } from 'react'
import type { FeedResponse, LibraryResponse, PaperState } from '@/types/api'

const apiPut = vi.fn()
const apiDelete = vi.fn()
vi.mock('@/lib/api-client', () => ({
  apiPut: (...args: unknown[]) => apiPut(...args),
  apiDelete: (...args: unknown[]) => apiDelete(...args),
}))
vi.mock('@/lib/notifications', () => ({
  notify: { success: vi.fn(), error: vi.fn(), undoable: vi.fn() },
}))

function seed(queryClient: QueryClient) {
  const items = [
    makeFeedItem({ paper: { ...makeFeedItem().paper, arxiv_id: 'a' } }),
    makeFeedItem({ paper: { ...makeFeedItem().paper, arxiv_id: 'b' } }),
  ]
  queryClient.setQueryData<FeedResponse>(feedKeys.list({}), makeFeedResponse(items))
  queryClient.setQueryData<FeedResponse>(
    feedKeys.list({ include_dismissed: true }),
    makeFeedResponse(items)
  )
  queryClient.setQueryData<FeedResponse>(
    feedKeys.list({ week: '2026-07-27' }),
    makeFeedResponse([makeFeedItem({ paper: { ...makeFeedItem().paper, arxiv_id: 'z' } })])
  )
}

function setup() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  })
  seed(queryClient)
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return { queryClient, wrapper }
}

function stateOf(state: PaperState['state']): PaperState {
  return { state, repo_url: null, dismissal_reason: null, updated_at: 'x' }
}

describe('applyStateToCaches', () => {
  it('removes a dismissed card from caches that hide dismissed and keeps it elsewhere', () => {
    const { queryClient } = setup()
    applyStateToCaches(queryClient, 'a', {
      state: 'dismissed',
      repo_url: null,
      dismissal_reason: null,
      updated_at: 'x',
    })

    const hidden = queryClient.getQueryData<FeedResponse>(feedKeys.list({}))!
    expect(hidden.items.map((i) => i.paper.arxiv_id)).toEqual(['b'])
    expect(hidden.total).toBe(1)

    const shown = queryClient.getQueryData<FeedResponse>(
      feedKeys.list({ include_dismissed: true })
    )!
    expect(shown.items.map((i) => i.paper.arxiv_id)).toEqual(['a', 'b'])
    expect(shown.items[0].state?.state).toBe('dismissed')
    expect(shown.total).toBe(2)
  })

  it('patches state in place for save', () => {
    const { queryClient } = setup()
    applyStateToCaches(queryClient, 'b', {
      state: 'saved',
      repo_url: null,
      dismissal_reason: null,
      updated_at: 'x',
    })
    const data = queryClient.getQueryData<FeedResponse>(feedKeys.list({}))!
    expect(data.items[1].state?.state).toBe('saved')
    expect(data.items[0].state).toBeNull()
  })

  it('leaves a cached week that does not hold the paper untouched', () => {
    const { queryClient } = setup()
    const otherKey = feedKeys.list({ week: '2026-07-27' })
    const before = queryClient.getQueryData<FeedResponse>(otherKey)
    applyStateToCaches(queryClient, 'a', stateOf('dismissed'))
    expect(queryClient.getQueryData<FeedResponse>(otherKey)).toBe(before)
  })
})

describe('applyStateToCaches (library)', () => {
  function seedLibrary(queryClient: QueryClient) {
    const saved = makeFeedItem({
      paper: { ...makeFeedItem().paper, arxiv_id: 'a' },
      state: stateOf('saved'),
    })
    const other = makeFeedItem({
      paper: { ...makeFeedItem().paper, arxiv_id: 'b' },
      state: stateOf('implementing'),
    })
    queryClient.setQueryData(
      libraryKeys.all,
      makeLibraryResponse({ saved: [saved], implementing: [other] })
    )
  }

  it('moves the card to the group of its new state, newest first', () => {
    const { queryClient } = setup()
    seedLibrary(queryClient)
    applyStateToCaches(queryClient, 'a', stateOf('implementing'))

    const library = queryClient.getQueryData<LibraryResponse>(libraryKeys.all)!
    expect(library.saved).toEqual([])
    expect(library.implementing.map((i) => i.paper.arxiv_id)).toEqual(['a', 'b'])
    expect(library.implementing[0].state?.state).toBe('implementing')
  })

  it('drops the card on dismiss or clear and ignores unknown papers', () => {
    const { queryClient } = setup()
    seedLibrary(queryClient)
    applyStateToCaches(queryClient, 'a', stateOf('dismissed'))
    applyStateToCaches(queryClient, 'b', null)
    applyStateToCaches(queryClient, 'zzz', stateOf('saved'))

    const library = queryClient.getQueryData<LibraryResponse>(libraryKeys.all)!
    expect(library).toEqual(makeLibraryResponse())
  })

  it('restores the library on a failed mutation', async () => {
    const { queryClient, wrapper } = setup()
    seedLibrary(queryClient)
    apiPut.mockRejectedValueOnce(new Error('boom'))
    const { result } = renderHook(() => useSetPaperState(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({ arxivId: 'a', body: { state: 'shipped' } }).catch(() => {})
    })

    await waitFor(() => {
      const library = queryClient.getQueryData<LibraryResponse>(libraryKeys.all)!
      expect(library.saved.map((i) => i.paper.arxiv_id)).toEqual(['a'])
      expect(library.shipped).toEqual([])
    })
  })
})

describe('applyStateToCaches (score detail)', () => {
  it('patches a ready score detail and leaves pending untouched', async () => {
    const { makePaperScoreDetail } = await import('../../../../fixtures/scores')
    const { queryClient } = setup()
    queryClient.setQueryData(scoreKeys.detail('a'), {
      status: 'ready',
      detail: makePaperScoreDetail(),
    })
    queryClient.setQueryData(scoreKeys.detail('b'), { status: 'pending', task_id: null })
    const next = {
      state: 'saved' as const,
      repo_url: null,
      dismissal_reason: null,
      updated_at: 'x',
    }
    const snap = applyStateToCaches(queryClient, 'a', next)
    expect(
      queryClient.getQueryData<{ status: string; detail: { state: unknown } }>(
        scoreKeys.detail('a')
      )?.detail.state
    ).toEqual(next)
    expect(snap.previousScore?.status).toBe('ready')
    applyStateToCaches(queryClient, 'b', next)
    expect(queryClient.getQueryData(scoreKeys.detail('b'))).toEqual({
      status: 'pending',
      task_id: null,
    })
  })
})

describe('useSetPaperState', () => {
  it('is optimistic and rolls back on error', async () => {
    const { queryClient, wrapper } = setup()
    let reject: (e: Error) => void = () => {}
    apiPut.mockReturnValueOnce(new Promise((_, r) => (reject = r)))
    const { result } = renderHook(() => useSetPaperState(), { wrapper })

    act(() => {
      result.current.mutate({ arxivId: 'a', body: { state: 'dismissed' } })
    })
    await waitFor(() => {
      const data = queryClient.getQueryData<FeedResponse>(feedKeys.list({}))!
      expect(data.items.map((i) => i.paper.arxiv_id)).toEqual(['b'])
    })

    act(() => reject(new Error('boom')))
    await waitFor(() => expect(result.current.isError).toBe(true))
    const restored = queryClient.getQueryData<FeedResponse>(feedKeys.list({}))!
    expect(restored.items.map((i) => i.paper.arxiv_id)).toEqual(['a', 'b'])
  })

  it('calls PUT with the body', async () => {
    const { wrapper } = setup()
    apiPut.mockResolvedValueOnce({
      state: 'saved',
      repo_url: null,
      dismissal_reason: null,
      updated_at: 'x',
    })
    const { result } = renderHook(() => useSetPaperState(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ arxivId: '2401.00001', body: { state: 'saved' } })
    })
    expect(apiPut).toHaveBeenCalledWith('/papers/2401.00001/state', { state: 'saved' })
  })
})

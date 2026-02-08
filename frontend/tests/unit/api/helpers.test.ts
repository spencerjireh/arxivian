import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement } from 'react'
import type { ReactNode } from 'react'
import { useOptimisticListMutation, useOptimisticMutation } from '../../../src/api/helpers'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  })
  return { queryClient, wrapper: ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children) }
}

describe('useOptimisticListMutation', () => {
  it('calls mutationFn with the provided variable', async () => {
    const { queryClient, wrapper } = createWrapper()

    queryClient.setQueryData(['items', 'list', {}], [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ])

    const mutationFn = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(
      () =>
        useOptimisticListMutation<Array<{ id: number; name: string }>, number>({
          mutationFn,
          listQueryKey: ['items', 'list'],
          updater: (old, deletedId) => old.filter((item) => item.id !== deletedId),
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate(1)
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(mutationFn).toHaveBeenCalledWith(1, expect.anything())
  })

  it('rolls back on error', async () => {
    const { queryClient, wrapper } = createWrapper()

    const original = [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ]
    queryClient.setQueryData(['items', 'list', {}], original)

    const mutationFn = vi.fn().mockRejectedValue(new Error('fail'))

    // Spy on setQueryData to verify rollback call happens
    const setQueryDataSpy = vi.spyOn(queryClient, 'setQueryData')

    const { result } = renderHook(
      () =>
        useOptimisticListMutation<Array<{ id: number; name: string }>, number>({
          mutationFn,
          listQueryKey: ['items', 'list'],
          updater: (old, deletedId) => old.filter((item) => item.id !== deletedId),
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate(1)
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    // Verify rollback restored the original data
    expect(setQueryDataSpy).toHaveBeenCalledWith(
      ['items', 'list', {}],
      original
    )
  })

  it('invalidates queries on settled', async () => {
    const { queryClient, wrapper } = createWrapper()

    queryClient.setQueryData(['items', 'list', {}], [{ id: 1 }])

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')
    const mutationFn = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(
      () =>
        useOptimisticListMutation<Array<{ id: number }>, number>({
          mutationFn,
          listQueryKey: ['items', 'list'],
          updater: (old, id) => old.filter((item) => item.id !== id),
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate(1)
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['items', 'list'] })
    )
  })
})

describe('useOptimisticMutation', () => {
  it('calls mutationFn with the provided variable', async () => {
    const { queryClient, wrapper } = createWrapper()

    queryClient.setQueryData(['prefs'], { items: ['a', 'b', 'c'] })

    const mutationFn = vi.fn().mockResolvedValue(undefined)

    const { result } = renderHook(
      () =>
        useOptimisticMutation<{ items: string[] }, string>({
          mutationFn,
          queryKey: ['prefs'],
          updater: (old, name) => ({
            ...old,
            items: old.items.filter((i) => i !== name),
          }),
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate('b')
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(mutationFn).toHaveBeenCalledWith('b', expect.anything())
  })

  it('rolls back on error', async () => {
    const { queryClient, wrapper } = createWrapper()

    const original = { items: ['a', 'b'] }
    queryClient.setQueryData(['prefs'], original)

    const mutationFn = vi.fn().mockRejectedValue(new Error('fail'))
    const setQueryDataSpy = vi.spyOn(queryClient, 'setQueryData')

    const { result } = renderHook(
      () =>
        useOptimisticMutation<{ items: string[] }, string>({
          mutationFn,
          queryKey: ['prefs'],
          updater: (old, name) => ({
            ...old,
            items: old.items.filter((i) => i !== name),
          }),
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate('a')
    })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    // Verify rollback restored the original data
    expect(setQueryDataSpy).toHaveBeenCalledWith(['prefs'], original)
  })

  it('does nothing when cache is empty', async () => {
    const { wrapper } = createWrapper()

    const mutationFn = vi.fn().mockResolvedValue(undefined)
    const updater = vi.fn()

    const { result } = renderHook(
      () =>
        useOptimisticMutation<{ items: string[] }, string>({
          mutationFn,
          queryKey: ['prefs'],
          updater,
        }),
      { wrapper }
    )

    await act(async () => {
      result.current.mutate('x')
    })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    // updater should not be called when there's no previous data
    expect(updater).not.toHaveBeenCalled()
  })
})

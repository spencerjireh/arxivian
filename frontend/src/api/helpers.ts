import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query'

interface OptimisticListMutationOptions<TList, TVariables> {
  mutationFn: (variables: TVariables) => Promise<unknown>
  listQueryKey: QueryKey
  updater: (old: TList, variables: TVariables) => TList
}

export function useOptimisticListMutation<TList, TVariables>({
  mutationFn,
  listQueryKey,
  updater,
}: OptimisticListMutationOptions<TList, TVariables>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn,
    onMutate: async (variables: TVariables) => {
      await queryClient.cancelQueries({ queryKey: listQueryKey })

      const previousLists = queryClient.getQueriesData<TList>({ queryKey: listQueryKey })

      queryClient.setQueriesData<TList>(
        { queryKey: listQueryKey },
        (old) => old ? updater(old, variables) : old
      )

      return { previousLists }
    },
    onError: (
      _err: unknown,
      _variables: TVariables,
      context: { previousLists?: [QueryKey, TList | undefined][] } | undefined
    ) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([key, data]) => {
          queryClient.setQueryData(key, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: listQueryKey })
    },
  })
}

interface OptimisticMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<unknown>
  queryKey: QueryKey
  updater: (old: TData, variables: TVariables) => TData
}

export function useOptimisticMutation<TData, TVariables>({
  mutationFn,
  queryKey,
  updater,
}: OptimisticMutationOptions<TData, TVariables>) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn,
    onMutate: async (variables: TVariables) => {
      await queryClient.cancelQueries({ queryKey })

      const previous = queryClient.getQueryData<TData>(queryKey)

      if (previous) {
        queryClient.setQueryData<TData>(queryKey, updater(previous, variables))
      }

      return { previous }
    },
    onError: (
      _err: unknown,
      _variables: TVariables,
      context: { previous?: TData } | undefined
    ) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  })
}

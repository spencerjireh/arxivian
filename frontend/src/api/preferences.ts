// Preferences REST API + TanStack Query hooks

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiDelete } from './client'
import type { UserPreferences, ArxivSearchConfig } from '../types/api'

// Query keys
export const preferencesKeys = {
  all: ['preferences'] as const,
  detail: () => [...preferencesKeys.all, 'detail'] as const,
}

// API functions
async function fetchPreferences(): Promise<UserPreferences> {
  return apiGet<UserPreferences>('/preferences')
}

async function addArxivSearch(config: ArxivSearchConfig): Promise<UserPreferences> {
  return apiPost<UserPreferences>('/preferences/arxiv-searches', config)
}

async function deleteArxivSearch(searchName: string): Promise<UserPreferences> {
  return apiDelete<UserPreferences>(
    `/preferences/arxiv-searches/${encodeURIComponent(searchName)}`
  )
}

// Hooks
export function usePreferences() {
  return useQuery({
    queryKey: preferencesKeys.detail(),
    queryFn: fetchPreferences,
  })
}

export function useAddArxivSearch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: addArxivSearch,
    onSuccess: (data) => {
      queryClient.setQueryData(preferencesKeys.detail(), data)
    },
  })
}

export function useDeleteArxivSearch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteArxivSearch,
    onMutate: async (searchName) => {
      await queryClient.cancelQueries({ queryKey: preferencesKeys.detail() })

      const previous = queryClient.getQueryData<UserPreferences>(preferencesKeys.detail())

      if (previous) {
        queryClient.setQueryData<UserPreferences>(preferencesKeys.detail(), {
          ...previous,
          arxiv_searches: previous.arxiv_searches.filter((s) => s.name !== searchName),
        })
      }

      return { previous }
    },
    onError: (_err, _name, context) => {
      if (context?.previous) {
        queryClient.setQueryData(preferencesKeys.detail(), context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: preferencesKeys.detail() })
    },
  })
}

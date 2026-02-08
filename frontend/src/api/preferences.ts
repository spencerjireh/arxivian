// Preferences REST API + TanStack Query hooks

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiPost, apiDelete } from './client'
import { useOptimisticMutation } from './helpers'
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
  return useOptimisticMutation<UserPreferences, string>({
    mutationFn: deleteArxivSearch,
    queryKey: preferencesKeys.detail(),
    updater: (old, searchName) => ({
      ...old,
      arxiv_searches: old.arxiv_searches.filter((s) => s.name !== searchName),
    }),
  })
}

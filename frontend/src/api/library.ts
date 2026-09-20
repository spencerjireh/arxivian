// Library REST API + TanStack Query hook (Phase 3, SPE-296)

import { useQuery } from '@tanstack/react-query'
import { apiGet } from './client'
import type { LibraryResponse } from '../types/api'

export const libraryKeys = {
  all: ['library'] as const,
}

export function useLibrary() {
  return useQuery({
    queryKey: libraryKeys.all,
    queryFn: () => apiGet<LibraryResponse>('/users/me/library'),
    staleTime: 60_000,
  })
}

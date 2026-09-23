// Library REST API + TanStack Query hook (Phase 3, SPE-296)

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api-client'
import { libraryKeys } from '@/lib/query-keys'
import type { LibraryResponse } from '@/types/api'

export function useLibrary() {
  return useQuery({
    queryKey: libraryKeys.all,
    queryFn: () => apiGet<LibraryResponse>('/users/me/library'),
    staleTime: 60_000,
  })
}

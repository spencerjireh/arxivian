// Papers REST API + TanStack Query hooks

import { useQuery } from '@tanstack/react-query'
import { apiGet, apiDelete } from './client'
import { useOptimisticListMutation } from './helpers'
import type {
  PaperListResponse,
  PaperListParams,
  DeletePaperResponse,
} from '../types/api'

// Query keys
export const paperKeys = {
  all: ['papers'] as const,
  lists: () => [...paperKeys.all, 'list'] as const,
  list: (params: PaperListParams) => [...paperKeys.lists(), params] as const,
}

// API functions
function buildPaperQuery(params: PaperListParams): string {
  const searchParams = new URLSearchParams()
  if (params.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params.processed_only !== undefined) searchParams.set('processed_only', String(params.processed_only))
  if (params.category) searchParams.set('category', params.category)
  if (params.author) searchParams.set('author', params.author)
  if (params.sort_by) searchParams.set('sort_by', params.sort_by)
  if (params.sort_order) searchParams.set('sort_order', params.sort_order)
  const qs = searchParams.toString()
  return `/papers${qs ? `?${qs}` : ''}`
}

async function fetchPapers(params: PaperListParams): Promise<PaperListResponse> {
  return apiGet<PaperListResponse>(buildPaperQuery(params))
}

async function deletePaper(arxivId: string): Promise<DeletePaperResponse> {
  return apiDelete<DeletePaperResponse>(`/papers/${encodeURIComponent(arxivId)}`)
}

// Hooks
export function usePapers(params: PaperListParams) {
  return useQuery({
    queryKey: paperKeys.list(params),
    queryFn: () => fetchPapers(params),
    staleTime: 60_000,
  })
}

export function useDeletePaper() {
  return useOptimisticListMutation<PaperListResponse, string>({
    mutationFn: deletePaper,
    listQueryKey: paperKeys.lists(),
    updater: (old, arxivId) => ({
      ...old,
      total: old.total - 1,
      papers: old.papers.filter((p) => p.arxiv_id !== arxivId),
    }),
  })
}

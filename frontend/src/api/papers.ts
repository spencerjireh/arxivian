// Papers REST API + TanStack Query hooks

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiDelete } from './client'
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
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deletePaper,
    onMutate: async (arxivId) => {
      await queryClient.cancelQueries({ queryKey: paperKeys.lists() })

      const previousLists = queryClient.getQueriesData({ queryKey: paperKeys.lists() })

      queryClient.setQueriesData<PaperListResponse>(
        { queryKey: paperKeys.lists() },
        (old) => {
          if (!old) return old
          return {
            ...old,
            total: old.total - 1,
            papers: old.papers.filter((p) => p.arxiv_id !== arxivId),
          }
        }
      )

      return { previousLists }
    },
    onError: (_err, _arxivId, context) => {
      if (context?.previousLists) {
        context.previousLists.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: paperKeys.lists() })
    },
  })
}

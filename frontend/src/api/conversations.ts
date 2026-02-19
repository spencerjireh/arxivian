// Conversation REST API + TanStack Query hooks

import { useQuery, useInfiniteQuery, useQueryClient, useMutation, type InfiniteData } from '@tanstack/react-query'
import { apiGet, apiDelete, apiPost } from './client'
import type {
  ConversationListResponse,
  ConversationDetailResponse,
  DeleteConversationResponse,
} from '../types/api'

interface ConfirmIngestRequest {
  approved: boolean
  selected_ids: string[]
}

interface ConfirmIngestResponse {
  acknowledged: boolean
  selected_count: number
}

const PAGE_SIZE = 30

// Query keys
export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  details: () => [...conversationKeys.all, 'detail'] as const,
  detail: (sessionId: string) => [...conversationKeys.details(), sessionId] as const,
}

// API functions
async function fetchConversations(
  offset: number,
  limit: number
): Promise<ConversationListResponse> {
  return apiGet<ConversationListResponse>(
    `/conversations?offset=${offset}&limit=${limit}`
  )
}

async function fetchConversation(
  sessionId: string
): Promise<ConversationDetailResponse> {
  return apiGet<ConversationDetailResponse>(`/conversations/${sessionId}`)
}

async function deleteConversation(
  sessionId: string
): Promise<DeleteConversationResponse> {
  return apiDelete<DeleteConversationResponse>(`/conversations/${sessionId}`)
}

export async function confirmIngest(
  sessionId: string,
  approved: boolean,
  selectedIds: string[]
): Promise<ConfirmIngestResponse> {
  return apiPost<ConfirmIngestResponse>(
    `/conversations/${sessionId}/confirm-ingest`,
    { approved, selected_ids: selectedIds } as ConfirmIngestRequest
  )
}

// Hooks
export function useInfiniteConversations() {
  return useInfiniteQuery({
    queryKey: conversationKeys.lists(),
    queryFn: ({ pageParam = 0 }) => fetchConversations(pageParam, PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const nextOffset = lastPage.offset + lastPage.limit
      return nextOffset < lastPage.total ? nextOffset : undefined
    },
  })
}

export function useConversation(sessionId: string | undefined) {
  return useQuery({
    queryKey: conversationKeys.detail(sessionId ?? ''),
    queryFn: () => fetchConversation(sessionId!),
    enabled: !!sessionId && sessionId !== 'new',
  })
}

export function useDeleteConversation() {
  const queryClient = useQueryClient()
  type Data = InfiniteData<ConversationListResponse>

  return useMutation({
    mutationFn: deleteConversation,
    onMutate: async (sessionId: string) => {
      await queryClient.cancelQueries({ queryKey: conversationKeys.lists() })

      const previous = queryClient.getQueryData<Data>(conversationKeys.lists())

      queryClient.setQueryData<Data>(conversationKeys.lists(), (old) => {
        if (!old) return old
        return {
          ...old,
          pages: old.pages.map((page) => ({
            ...page,
            total: page.total - 1,
            conversations: page.conversations.filter((c) => c.session_id !== sessionId),
          })),
        }
      })

      return { previous }
    },
    onError: (_err, _sessionId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(conversationKeys.lists(), context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
    },
  })
}

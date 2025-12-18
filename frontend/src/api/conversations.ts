// Conversation REST API + TanStack Query hooks

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiGet, apiDelete } from './client'
import type {
  ConversationListResponse,
  ConversationDetailResponse,
  DeleteConversationResponse,
} from '../types/api'

// Query keys
export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  list: (offset: number, limit: number) =>
    [...conversationKeys.lists(), { offset, limit }] as const,
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

// Hooks
export function useConversations(offset: number = 0, limit: number = 20) {
  return useQuery({
    queryKey: conversationKeys.list(offset, limit),
    queryFn: () => fetchConversations(offset, limit),
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

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      // Invalidate conversation list to refetch
      queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
    },
  })
}

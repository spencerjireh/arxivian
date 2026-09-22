// Conversation REST API + TanStack Query hooks (paper-scoped threads only)

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api-client'
import { conversationKeys } from '@/lib/query-keys'
import type { ConversationListResponse, ConversationDetailResponse } from '@/types/api'

const PAGE_SIZE = 30

async function fetchConversation(sessionId: string): Promise<ConversationDetailResponse> {
  return apiGet<ConversationDetailResponse>(`/conversations/${sessionId}`)
}

async function fetchPaperConversations(arxivId: string): Promise<ConversationListResponse> {
  return apiGet<ConversationListResponse>(
    `/conversations?arxiv_id=${encodeURIComponent(arxivId)}&offset=0&limit=${PAGE_SIZE}`
  )
}

/** Threads scoped to one paper (paper detail chat panel). */
export function usePaperConversations(arxivId: string | undefined) {
  return useQuery({
    queryKey: conversationKeys.paperList(arxivId ?? ''),
    queryFn: () => fetchPaperConversations(arxivId!),
    enabled: !!arxivId,
    staleTime: 60_000,
  })
}

export function useConversation(sessionId: string | undefined) {
  return useQuery({
    queryKey: conversationKeys.detail(sessionId ?? ''),
    queryFn: () => fetchConversation(sessionId!),
    enabled: !!sessionId && sessionId !== 'new',
  })
}

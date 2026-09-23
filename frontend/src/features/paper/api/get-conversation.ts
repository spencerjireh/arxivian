// Conversation REST API (paper-scoped threads only): the thread list for a paper, one thread's
// turns, and the turn -> Message mapping the chat cache renders.

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/lib/api-client'
import { conversationKeys } from '@/lib/query-keys'
import type {
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationTurn,
  Message,
} from '@/types/api'

const PAGE_SIZE = 30

export async function fetchConversation(sessionId: string): Promise<ConversationDetailResponse> {
  return apiGet<ConversationDetailResponse>(`/conversations/${sessionId}`)
}

async function fetchPaperConversations(arxivId: string): Promise<ConversationListResponse> {
  return apiGet<ConversationListResponse>(
    `/conversations?arxiv_id=${encodeURIComponent(arxivId)}&offset=0&limit=${PAGE_SIZE}`
  )
}

/** A stored turn becomes the user message and the assistant message the panel renders. */
export function turnsToMessages(turns: ConversationTurn[]): Message[] {
  return turns.flatMap((turn): Message[] => [
    {
      id: `user-${turn.turn_number}`,
      role: 'user',
      content: turn.user_query,
      createdAt: new Date(turn.created_at),
    },
    {
      id: `assistant-${turn.turn_number}`,
      role: 'assistant',
      content: turn.agent_response,
      sources: turn.sources ?? undefined,
      metadata: {
        query: turn.user_query,
        execution_time_ms: 0,
        retrieval_attempts: turn.retrieval_attempts,
        guardrail_score: turn.guardrail_score,
        session_id: null,
        turn_number: turn.turn_number,
      },
      citations: turn.citations ?? undefined,
      createdAt: new Date(turn.created_at),
    },
  ])
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

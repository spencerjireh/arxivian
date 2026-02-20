import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useChatStore } from '../stores/chatStore'
import { hydrateThinkingSteps } from '../lib/thinking'
import type {
  Message,
  PersistedThinkingStep,
  CitationsEventData,
  ConfirmIngestEventData,
} from '../types/api'

export const chatKeys = {
  messages: (sessionId: string | null) => ['chat', 'messages', sessionId] as const,
}

export function useMessageCache(sessionId: string | null) {
  const queryClient = useQueryClient()
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)

  // Subscribe to messages in query cache (reactive)
  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: chatKeys.messages(sessionId),
    queryFn: () => [],
    staleTime: Infinity,
    gcTime: Infinity,
  })

  const setMessages = useCallback(
    (updater: Message[] | ((prev: Message[]) => Message[])) => {
      queryClient.setQueryData<Message[]>(chatKeys.messages(sessionId), (prev) => {
        const prevMessages = prev ?? []
        return typeof updater === 'function' ? updater(prevMessages) : updater
      })
    },
    [queryClient, sessionId]
  )

  const loadFromHistory = useCallback(
    (
      turns: Array<{
        turn_number: number
        user_query: string
        agent_response: string
        provider: string
        model: string
        guardrail_score?: number | null
        retrieval_attempts: number
        rewritten_query?: string | null
        sources?: Record<string, unknown>[] | null
        reasoning_steps?: string[] | null
        thinking_steps?: PersistedThinkingStep[] | null
        citations?: Record<string, unknown> | null
        pending_confirmation?: ConfirmIngestEventData | null
        created_at: string
      }>
    ) => {
      const loadedMessages: Message[] = turns.flatMap((turn) => [
        {
          id: `user-${turn.turn_number}`,
          role: 'user' as const,
          content: turn.user_query,
          createdAt: new Date(turn.created_at),
        },
        {
          id: `assistant-${turn.turn_number}`,
          role: 'assistant' as const,
          content: turn.agent_response,
          sources: turn.sources?.map((s) => s as unknown as import('../types/api').SourceInfo),
          metadata: {
            query: turn.user_query,
            execution_time_ms: 0,
            retrieval_attempts: turn.retrieval_attempts,
            rewritten_query: turn.rewritten_query ?? undefined,
            guardrail_score: turn.guardrail_score ?? undefined,
            provider: turn.provider,
            model: turn.model,
            turn_number: turn.turn_number,
            reasoning_steps: turn.reasoning_steps ?? [],
          },
          thinkingSteps: hydrateThinkingSteps(turn.thinking_steps),
          citations: (turn.citations as CitationsEventData) ?? undefined,
          ingestProposal: turn.pending_confirmation ?? undefined,
          createdAt: new Date(turn.created_at),
        },
      ])
      setMessages(loadedMessages)
    },
    [setMessages]
  )

  const clearMessages = useCallback(() => {
    queryClient.setQueryData(chatKeys.messages(sessionId), [])
    resetStreamingState()
  }, [queryClient, sessionId, resetStreamingState])

  return {
    messages,
    setMessages,
    loadFromHistory,
    clearMessages,
  }
}

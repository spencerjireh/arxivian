// useMessageCache: TanStack Query cache of a thread's turns (GET /conversations/{id}), keyed per paper for drafts.
import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useChatStore } from '../stores/chatStore'
import type { Message, SourceInfo, CitationsEventData, ConversationTurn } from '../types/api'

export const chatKeys = {
  /** A draft (sessionId null) is keyed by its paper so panels never share a draft. */
  messages: (sessionId: string | null, scope?: string) =>
    scope && sessionId === null
      ? (['chat', 'messages', null, scope] as const)
      : (['chat', 'messages', sessionId] as const),
}

export function useMessageCache(sessionId: string | null, scope?: string) {
  const queryClient = useQueryClient()
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)

  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: chatKeys.messages(sessionId, scope),
    queryFn: () => [],
    staleTime: Infinity,
    gcTime: Infinity,
  })

  const setMessages = useCallback(
    (updater: Message[] | ((prev: Message[]) => Message[])) => {
      queryClient.setQueryData<Message[]>(chatKeys.messages(sessionId, scope), (prev) => {
        const prevMessages = prev ?? []
        return typeof updater === 'function' ? updater(prevMessages) : updater
      })
    },
    [queryClient, sessionId, scope]
  )

  const loadFromHistory = useCallback(
    (turns: ConversationTurn[]) => {
      setMessages(
        turns.flatMap((turn): Message[] => [
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
            sources: (turn.sources as SourceInfo[] | null) ?? undefined,
            metadata: {
              query: turn.user_query,
              execution_time_ms: 0,
              retrieval_attempts: turn.retrieval_attempts,
              guardrail_score: turn.guardrail_score ?? undefined,
              turn_number: turn.turn_number,
            },
            citations: (turn.citations as CitationsEventData | null) ?? undefined,
            createdAt: new Date(turn.created_at),
          },
        ])
      )
    },
    [setMessages]
  )

  const clearMessages = useCallback(() => {
    queryClient.setQueryData(chatKeys.messages(sessionId, scope), [])
    resetStreamingState()
  }, [queryClient, sessionId, scope, resetStreamingState])

  return { messages, setMessages, loadFromHistory, clearMessages }
}

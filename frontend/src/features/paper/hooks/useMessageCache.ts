// useMessageCache: a thread's messages in the TanStack Query cache. A real session id fetches
// GET /conversations/{id} once; a draft (null session) is keyed per paper and starts empty.
import { useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useChatStore } from '@/stores/chatStore'
import { fetchConversation, turnsToMessages } from '../api/get-conversation'
import type { Message } from '@/types/api'

export const chatKeys = {
  /** A draft (sessionId null) is keyed by its paper so panels never share a draft. */
  messages: (sessionId: string | null, scope?: string) =>
    scope && sessionId === null
      ? (['chat', 'messages', null, scope] as const)
      : (['chat', 'messages', sessionId] as const),
}

export function useMessageCache(sessionId: string | null, scope: string) {
  const queryClient = useQueryClient()
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)
  const queryKey = chatKeys.messages(sessionId, scope)

  // Streaming writes go through setMessages, so cached data is never stale and never
  // refetched: a thread the first turn just created under a new id is not clobbered.
  const { data: messages = [], isPending } = useQuery<Message[]>({
    queryKey,
    queryFn: () => fetchConversation(sessionId!).then((c) => turnsToMessages(c.turns)),
    enabled: sessionId !== null,
    initialData: sessionId === null ? [] : undefined,
    staleTime: Infinity,
    gcTime: Infinity,
  })

  const setMessages = useCallback(
    (updater: Message[] | ((prev: Message[]) => Message[])) => {
      queryClient.setQueryData<Message[]>(queryKey, (prev) => {
        const prevMessages = prev ?? []
        return typeof updater === 'function' ? updater(prevMessages) : updater
      })
    },
    [queryClient, queryKey]
  )

  const clearMessages = useCallback(() => {
    queryClient.setQueryData(queryKey, [])
    resetStreamingState()
  }, [queryClient, queryKey, resetStreamingState])

  return {
    messages,
    isLoadingHistory: sessionId !== null && isPending,
    setMessages,
    clearMessages,
  }
}

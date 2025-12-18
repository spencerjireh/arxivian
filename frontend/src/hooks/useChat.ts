// Unified chat hook combining TanStack Query with SSE streaming
// This hook manages all chat state through the query cache for consistency

import { useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { streamChat, createStreamAbortController, StreamAbortError } from '../api/stream'
import { conversationKeys } from '../api/conversations'
import { useChatStore } from '../stores/chatStore'
import { DEFAULT_SETTINGS } from '../stores/settingsStore'
import type {
  StreamRequest,
  LLMProvider,
  Message,
  SourceInfo,
  MetadataEventData,
} from '../types/api'

export interface ChatOptions {
  provider?: LLMProvider
  model?: string
  temperature: number
  top_k: number
  guardrail_threshold: number
  max_retrieval_attempts: number
  conversation_window: number
}

// Query key for current chat messages (separate from persisted conversations)
export const chatKeys = {
  messages: (sessionId: string | null) => ['chat', 'messages', sessionId] as const,
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const abortControllerRef = useRef<AbortController | null>(null)

  // UI-only state from Zustand (streaming status, current streaming content)
  const {
    isStreaming,
    streamingContent,
    currentStatus,
    sources,
    error,
    setStreaming,
    appendStreamingContent,
    setStatus,
    setSources,
    setError,
    resetStreamingState,
  } = useChatStore()

  // Get current messages from query cache
  const messages: Message[] =
    queryClient.getQueryData<Message[]>(chatKeys.messages(sessionId)) ?? []

  // Set messages in query cache
  const setMessages = useCallback(
    (updater: Message[] | ((prev: Message[]) => Message[])) => {
      queryClient.setQueryData<Message[]>(chatKeys.messages(sessionId), (prev) => {
        const prevMessages = prev ?? []
        return typeof updater === 'function' ? updater(prevMessages) : updater
      })
    },
    [queryClient, sessionId]
  )

  // Add a user message
  const addUserMessage = useCallback(
    (content: string) => {
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content,
        createdAt: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])
    },
    [setMessages]
  )

  // Finalize assistant message after streaming completes
  const finalizeAssistantMessage = useCallback(
    (content: string, sources: SourceInfo[], metadata: MetadataEventData) => {
      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content,
        sources: sources.length > 0 ? sources : undefined,
        metadata,
        createdAt: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      // If this was a new chat and we got a session_id back, handle navigation
      if (metadata.session_id && sessionId === null) {
        // Move messages to the new session's cache
        const currentMessages = queryClient.getQueryData<Message[]>(chatKeys.messages(null)) ?? []
        const updatedMessages = [...currentMessages, assistantMessage]

        // Set messages in the new session's cache
        queryClient.setQueryData(chatKeys.messages(metadata.session_id), updatedMessages)

        // Clear the null session cache
        queryClient.setQueryData(chatKeys.messages(null), [])

        // Invalidate conversation list so it refetches and shows the new conversation
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })

        // Navigate to the new session URL
        navigate(`/${metadata.session_id}`, { replace: true })
      } else {
        // Existing session - just invalidate the list to update "last_query"
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
      }
    },
    [setMessages, sessionId, queryClient, navigate]
  )

  // Send a message
  const sendMessage = useCallback(
    async (query: string, options: ChatOptions) => {
      if (isStreaming) {
        return
      }

      // Add user message immediately
      addUserMessage(query)

      // Reset streaming state and start
      resetStreamingState()
      setStreaming(true)
      setError(null)

      // Create abort controller
      abortControllerRef.current = createStreamAbortController()

      // Build request - only include non-default values
      const request: StreamRequest = {
        query,
        session_id: sessionId ?? undefined,
      }

      if (options.provider !== DEFAULT_SETTINGS.provider) {
        request.provider = options.provider
      }
      if (options.model !== DEFAULT_SETTINGS.model) {
        request.model = options.model
      }
      if (options.temperature !== DEFAULT_SETTINGS.temperature) {
        request.temperature = options.temperature
      }
      if (options.top_k !== DEFAULT_SETTINGS.top_k) {
        request.top_k = options.top_k
      }
      if (options.guardrail_threshold !== DEFAULT_SETTINGS.guardrail_threshold) {
        request.guardrail_threshold = options.guardrail_threshold
      }
      if (options.max_retrieval_attempts !== DEFAULT_SETTINGS.max_retrieval_attempts) {
        request.max_retrieval_attempts = options.max_retrieval_attempts
      }
      if (options.conversation_window !== DEFAULT_SETTINGS.conversation_window) {
        request.conversation_window = options.conversation_window
      }

      let accumulatedContent = ''
      let accumulatedSources: SourceInfo[] = []

      try {
        await streamChat(
          request,
          {
            onStatus: (data) => {
              setStatus(data.message)
            },
            onContent: (data) => {
              accumulatedContent += data.token
              appendStreamingContent(data.token)
            },
            onSources: (data) => {
              accumulatedSources = data.sources
              setSources(data.sources)
            },
            onMetadata: (data) => {
              // Finalize the message with all accumulated data
              finalizeAssistantMessage(accumulatedContent, accumulatedSources, data)
              resetStreamingState()
              setStreaming(false)
            },
            onError: (data) => {
              setError(data.error)
              setStreaming(false)
            },
            onDone: () => {
              setStatus(null)
            },
          },
          abortControllerRef.current
        )
      } catch (err) {
        if (err instanceof StreamAbortError) {
          // User cancelled - not an error
          resetStreamingState()
          setStreaming(false)
          return
        }
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        setError(errorMessage)
        setStreaming(false)
      } finally {
        abortControllerRef.current = null
      }
    },
    [
      isStreaming,
      sessionId,
      addUserMessage,
      resetStreamingState,
      setStreaming,
      setError,
      setStatus,
      appendStreamingContent,
      setSources,
      finalizeAssistantMessage,
    ]
  )

  // Cancel the current stream
  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

  // Load messages from conversation history (when navigating to existing chat)
  const loadFromHistory = useCallback(
    (turns: Array<{
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
      created_at: string
    }>) => {
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
          sources: turn.sources?.map((s) => s as unknown as SourceInfo),
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
          createdAt: new Date(turn.created_at),
        },
      ])
      setMessages(loadedMessages)
    },
    [setMessages]
  )

  // Clear messages for this session
  const clearMessages = useCallback(() => {
    queryClient.setQueryData(chatKeys.messages(sessionId), [])
    resetStreamingState()
  }, [queryClient, sessionId, resetStreamingState])

  return {
    // State
    messages,
    isStreaming,
    streamingContent,
    currentStatus,
    sources,
    error,

    // Actions
    sendMessage,
    cancelStream,
    loadFromHistory,
    clearMessages,
  }
}

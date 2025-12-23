import { useCallback, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { streamChat, createStreamAbortController, StreamAbortError } from '../api/stream'
import { conversationKeys } from '../api/conversations'
import { useChatStore } from '../stores/chatStore'
import { DEFAULT_SETTINGS } from '../stores/settingsStore'
import { generateMessageId } from '../utils/id'
import type {
  StreamRequest,
  LLMProvider,
  Message,
  SourceInfo,
  MetadataEventData,
  ThinkingStep,
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

export const chatKeys = {
  messages: (sessionId: string | null) => ['chat', 'messages', sessionId] as const,
}

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const abortControllerRef = useRef<AbortController | null>(null)
  const streamingMessageIdRef = useRef<string | null>(null)

  // Get store actions (these are stable references)
  // Note: Don't destructure state values here - they become stale in callbacks
  const setStreaming = useChatStore((s) => s.setStreaming)
  const appendStreamingContent = useChatStore((s) => s.appendStreamingContent)
  const setStatus = useChatStore((s) => s.setStatus)
  const setSources = useChatStore((s) => s.setSources)
  const setError = useChatStore((s) => s.setError)
  const addThinkingStep = useChatStore((s) => s.addThinkingStep)
  const getThinkingSteps = useChatStore((s) => s.getThinkingSteps)
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)

  // Subscribe to messages in query cache (reactive)
  const { data: messages = [] } = useQuery<Message[]>({
    queryKey: chatKeys.messages(sessionId),
    queryFn: () => {
      // When creating a new query for a session, check if there's data in the null cache
      // This handles the race condition when navigating from new chat to session
      if (sessionId !== null) {
        const nullCacheMessages = queryClient.getQueryData<Message[]>(chatKeys.messages(null))
        if (nullCacheMessages && nullCacheMessages.length > 0) {
          // Copy messages from null cache to session cache
          queryClient.setQueryData(chatKeys.messages(sessionId), nullCacheMessages)
          return nullCacheMessages
        }
      }
      return []
    },
    staleTime: Infinity,
    gcTime: Infinity,
  })

  // Ensure cache continuity when sessionId changes from null to actual ID
  // This runs AFTER navigation completes and component re-renders
  useEffect(() => {
    if (sessionId !== null) {
      // Check if current session cache is empty
      const sessionCache = queryClient.getQueryData<Message[]>(chatKeys.messages(sessionId))
      const nullCache = queryClient.getQueryData<Message[]>(chatKeys.messages(null))

      // If session cache is empty but null cache has messages, copy them over
      if ((!sessionCache || sessionCache.length === 0) && nullCache && nullCache.length > 0) {
        queryClient.setQueryData(chatKeys.messages(sessionId), nullCache)
      }
    }
  }, [sessionId, queryClient])

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

  const addUserMessage = useCallback(
    (content: string) => {
      const userMessage: Message = {
        id: generateMessageId(),
        role: 'user',
        content,
        createdAt: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])
    },
    [setMessages]
  )

  const addStreamingPlaceholder = useCallback(() => {
    const placeholderMessage: Message = {
      id: generateMessageId(),
      role: 'assistant',
      content: '',
      isStreaming: true,
      createdAt: new Date(),
    }
    setMessages((prev) => [...prev, placeholderMessage])
    return placeholderMessage.id
  }, [setMessages])

  const updateStreamingMessage = useCallback(
    (id: string, updates: Partial<Message>) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === id && msg.isStreaming ? { ...msg, ...updates, isStreaming: true } : msg
        )
      )
    },
    [setMessages]
  )

  const finalizeAssistantMessage = useCallback(
    (
      placeholderId: string | null,
      content: string,
      sources: SourceInfo[],
      metadata: MetadataEventData,
      thinkingSteps: ThinkingStep[]
    ) => {
      const finalizedSteps = thinkingSteps.map((step) => ({
        ...step,
        status: 'complete' as const,
      }))

      const assistantMessage: Message = {
        id: placeholderId || generateMessageId(),
        role: 'assistant',
        content,
        sources: sources.length > 0 ? sources : undefined,
        metadata,
        thinkingSteps: finalizedSteps.length > 0 ? finalizedSteps : undefined,
        isStreaming: false,
        createdAt: new Date(),
      }

      if (metadata.session_id && sessionId === null) {
        const currentMessages = queryClient.getQueryData<Message[]>(chatKeys.messages(null)) ?? []

        // Replace placeholder with finalized message
        const updatedMessages = currentMessages.map((msg) =>
          msg.id === placeholderId ? assistantMessage : msg
        )

        // Update null cache (source of truth until navigation completes)
        queryClient.setQueryData(chatKeys.messages(null), updatedMessages)
        // Pre-populate session cache (will be copied by useEffect if needed)
        queryClient.setQueryData(chatKeys.messages(metadata.session_id), updatedMessages)
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })

        // Navigate - useEffect will ensure cache continuity
        navigate(`/${metadata.session_id}`, { replace: true })
      } else {
        // Replace placeholder with finalized message
        setMessages((prev) => prev.map((msg) => (msg.id === placeholderId ? assistantMessage : msg)))
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
      }
    },
    [setMessages, sessionId, queryClient, navigate]
  )

  const buildStreamRequest = useCallback(
    (query: string, options: ChatOptions): StreamRequest => {
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

      return request
    },
    [sessionId]
  )

  const sendMessage = useCallback(
    async (query: string, options: ChatOptions) => {
      if (useChatStore.getState().isStreaming) {
        return
      }

      addUserMessage(query)
      resetStreamingState()
      setStreaming(true)
      setError(null)

      const streamingMessageId = addStreamingPlaceholder()
      streamingMessageIdRef.current = streamingMessageId

      abortControllerRef.current = createStreamAbortController()

      const request = buildStreamRequest(query, options)
      let accumulatedContent = ''
      let accumulatedSources: SourceInfo[] = []

      try {
        await streamChat(
          request,
          {
            onStatus: (data) => {
              setStatus(data.message)
              addThinkingStep(data)
              const currentSteps = getThinkingSteps()
              if (streamingMessageIdRef.current) {
                updateStreamingMessage(streamingMessageIdRef.current, {
                  thinkingSteps: currentSteps,
                })
              }
            },
            onContent: (data) => {
              accumulatedContent += data.token
              appendStreamingContent(data.token)
              if (streamingMessageIdRef.current) {
                updateStreamingMessage(streamingMessageIdRef.current, {
                  content: accumulatedContent,
                })
              }
            },
            onSources: (data) => {
              accumulatedSources = data.sources
              setSources(data.sources)
              if (streamingMessageIdRef.current) {
                updateStreamingMessage(streamingMessageIdRef.current, {
                  sources: data.sources,
                })
              }
            },
            onMetadata: (data) => {
              const finalThinkingSteps = getThinkingSteps()
              finalizeAssistantMessage(
                streamingMessageIdRef.current,
                accumulatedContent,
                accumulatedSources,
                data,
                finalThinkingSteps
              )
              streamingMessageIdRef.current = null
              // Don't reset state here - it will be reset at start of next message
              // Resetting here causes rapid re-renders that interrupt animations
              setStreaming(false)
            },
            onError: (data) => {
              if (streamingMessageIdRef.current) {
                setMessages((prev) => prev.filter((msg) => msg.id !== streamingMessageIdRef.current))
                streamingMessageIdRef.current = null
              }
              resetStreamingState()
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
          // User cancelled - remove placeholder
          if (streamingMessageIdRef.current) {
            setMessages((prev) => prev.filter((msg) => msg.id !== streamingMessageIdRef.current))
            streamingMessageIdRef.current = null
          }
          resetStreamingState()
          setStreaming(false)
          return
        }
        // Remove placeholder on error
        if (streamingMessageIdRef.current) {
          setMessages((prev) => prev.filter((msg) => msg.id !== streamingMessageIdRef.current))
          streamingMessageIdRef.current = null
        }
        resetStreamingState()
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        setError(errorMessage)
        setStreaming(false)
      } finally {
        abortControllerRef.current = null
      }
    },
    [
      addUserMessage,
      addStreamingPlaceholder,
      updateStreamingMessage,
      buildStreamRequest,
      resetStreamingState,
      setStreaming,
      setError,
      setStatus,
      appendStreamingContent,
      setSources,
      addThinkingStep,
      getThinkingSteps,
      finalizeAssistantMessage,
      setMessages,
    ]
  )

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

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

  const clearMessages = useCallback(() => {
    queryClient.setQueryData(chatKeys.messages(sessionId), [])
    resetStreamingState()
  }, [queryClient, sessionId, resetStreamingState])

  return {
    messages,
    sendMessage,
    cancelStream,
    loadFromHistory,
    clearMessages,
  }
}

// SSE + store orchestration hook

import { useRef, useCallback } from 'react'
import { streamChat, createStreamAbortController, StreamAbortError } from '../api/stream'
import { useChatStore } from '../stores/chatStore'
import type { StreamRequest, LLMProvider } from '../types/api'

export interface ChatOptions {
  provider?: LLMProvider
  model?: string
  temperature?: number
  top_k?: number
  guardrail_threshold?: number
  max_retrieval_attempts?: number
  conversation_window?: number
}

export function useStreamChat() {
  const abortControllerRef = useRef<AbortController | null>(null)

  const {
    sessionId,
    isStreaming,
    addUserMessage,
    startAssistantMessage,
    appendToken,
    setStatus,
    setSources,
    finalizeMessage,
    setError,
  } = useChatStore()

  const sendMessage = useCallback(
    async (query: string, options: ChatOptions = {}) => {
      if (isStreaming) {
        return
      }

      // Add user message to store
      addUserMessage(query)
      startAssistantMessage()

      // Create abort controller for this stream
      abortControllerRef.current = createStreamAbortController()

      const request: StreamRequest = {
        query,
        session_id: sessionId ?? undefined,
        ...options,
      }

      try {
        await streamChat(
          request,
          {
            onStatus: (data) => {
              setStatus(data.message)
            },
            onContent: (data) => {
              appendToken(data.token)
            },
            onSources: (data) => {
              setSources(data.sources)
            },
            onMetadata: (data) => {
              finalizeMessage(data)
            },
            onError: (data) => {
              setError(data.error)
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
          setStatus(null)
          return
        }
        const errorMessage =
          err instanceof Error ? err.message : 'An unexpected error occurred'
        setError(errorMessage)
      } finally {
        abortControllerRef.current = null
      }
    },
    [
      sessionId,
      isStreaming,
      addUserMessage,
      startAssistantMessage,
      appendToken,
      setStatus,
      setSources,
      finalizeMessage,
      setError,
    ]
  )

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

  return {
    sendMessage,
    cancelStream,
    isStreaming,
  }
}

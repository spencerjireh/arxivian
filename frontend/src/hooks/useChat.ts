import { useCallback, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { streamChat, StreamAbortError, StreamError } from '../api/stream'
import { conversationKeys } from '../api/conversations'
import { useChatStore } from '../stores/chatStore'
import { useUserStore } from '../stores/userStore'
import { generateMessageId } from '../utils/id'
import { useMessageCache, chatKeys } from './useMessageCache'
import { getErrorTreatment } from '../lib/errorMapping'
import type { StreamCallbacks } from '../api/stream'
import type {
  Message,
  MessageError,
  SourceInfo,
  MetadataEventData,
  CitationsEventData,
} from '../types/api'

export { chatKeys } from './useMessageCache'

export interface UseChatOptions {
  /** The paper this conversation is scoped to; sent as `arxiv_id` on every turn. */
  arxivId: string
  /** Called with the new session id after the first turn of a draft. */
  onSessionCreated?: (sessionId: string) => void
}

/**
 * Chat state + streaming for one paper-scoped conversation.
 *
 * The streaming UI state lives in the global `useChatStore`, so only one chat surface may
 * be mounted at a time; the panel aborts its stream on unmount.
 */
export function useChat(sessionId: string | null, options: UseChatOptions) {
  const queryClient = useQueryClient()
  const abortControllerRef = useRef<AbortController | null>(null)
  const streamingMessageIdRef = useRef<string | null>(null)
  const optionsRef = useRef(options)
  useEffect(() => {
    optionsRef.current = options
  })
  const scope = options.arxivId

  const { messages, setMessages, loadFromHistory, clearMessages } = useMessageCache(
    sessionId,
    scope
  )

  const setStreaming = useChatStore((s) => s.setStreaming)
  const appendStreamingContent = useChatStore((s) => s.appendStreamingContent)
  const setStatus = useChatStore((s) => s.setStatus)
  const setSources = useChatStore((s) => s.setSources)
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)

  const addStreamingPlaceholder = useCallback(() => {
    const placeholder: Message = {
      id: generateMessageId(),
      role: 'assistant',
      content: '',
      isStreaming: true,
      createdAt: new Date(),
    }
    setMessages((prev) => [...prev, placeholder])
    return placeholder.id
  }, [setMessages])

  const updateStreamingMessage = useCallback(
    (id: string, updates: Partial<Message>) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === id && msg.isStreaming
            ? { ...msg, ...updates, isStreaming: updates.isStreaming ?? true }
            : msg
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
      citations?: CitationsEventData
    ) => {
      const assistantMessage: Message = {
        id: placeholderId || generateMessageId(),
        role: 'assistant',
        content,
        sources: sources.length > 0 ? sources : undefined,
        metadata,
        citations,
        isStreaming: false,
        createdAt: new Date(),
      }

      if (metadata.session_id && sessionId === null) {
        // First turn of a draft: move the messages under the new session id.
        const draftKey = chatKeys.messages(null, scope)
        const draft = queryClient.getQueryData<Message[]>(draftKey) ?? []
        queryClient.setQueryData(
          chatKeys.messages(metadata.session_id),
          draft.map((msg) => (msg.id === placeholderId ? assistantMessage : msg))
        )
        queryClient.setQueryData(draftKey, [])
        optionsRef.current.onSessionCreated?.(metadata.session_id)
      } else {
        setMessages((prev) =>
          prev.map((msg) => (msg.id === placeholderId ? assistantMessage : msg))
        )
      }
      void queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
    },
    [setMessages, sessionId, scope, queryClient]
  )

  const handleStreamError = useCallback(
    (code: string, message: string) => {
      const treatment = getErrorTreatment(code, message)
      const placeholderId = streamingMessageIdRef.current
      streamingMessageIdRef.current = null

      if (placeholderId) {
        if (treatment.display === 'inline') {
          const error: MessageError = { message, code }
          updateStreamingMessage(placeholderId, { isStreaming: false, error })
        } else {
          setMessages((prev) => prev.filter((msg) => msg.id !== placeholderId))
        }
      }
      if (treatment.display === 'toast') {
        toast.error(treatment.title, { description: treatment.body ?? message })
      }
      resetStreamingState()
      setStreaming(false)
    },
    [setMessages, updateStreamingMessage, resetStreamingState, setStreaming]
  )

  const executeQueryStream = useCallback(
    async (query: string) => {
      resetStreamingState()
      setStreaming(true)
      streamingMessageIdRef.current = addStreamingPlaceholder()
      abortControllerRef.current = new AbortController()

      const acc = {
        content: '',
        sources: [] as SourceInfo[],
        citations: undefined as CitationsEventData | undefined,
      }
      const patch = (updates: Partial<Message>) => {
        if (streamingMessageIdRef.current) {
          updateStreamingMessage(streamingMessageIdRef.current, updates)
        }
      }

      const callbacks: StreamCallbacks = {
        onStatus: (data) => setStatus(data.message),
        onContent: (data) => {
          acc.content += data.token
          appendStreamingContent(data.token)
          patch({ content: acc.content })
        },
        onSources: (data) => {
          acc.sources = data.sources
          setSources(data.sources)
          patch({ sources: data.sources })
        },
        onCitations: (data) => {
          acc.citations = data
          patch({ citations: data })
        },
        onMetadata: (data) => {
          finalizeAssistantMessage(
            streamingMessageIdRef.current,
            acc.content,
            acc.sources,
            data,
            acc.citations
          )
          streamingMessageIdRef.current = null
          setStreaming(false)
        },
        onError: (data) => handleStreamError(data.code ?? 'INTERNAL_ERROR', data.error),
        onDone: () => setStatus(null),
      }

      try {
        await streamChat(
          { query, arxiv_id: optionsRef.current.arxivId, session_id: sessionId ?? undefined },
          callbacks,
          abortControllerRef.current
        )
      } catch (err) {
        if (err instanceof StreamAbortError) {
          handleStreamError('CANCELLED', 'Stream aborted')
          return
        }
        const code = err instanceof StreamError ? err.code : 'INTERNAL_ERROR'
        const message = err instanceof Error ? err.message : 'An unexpected error occurred'
        handleStreamError(code, message)
      } finally {
        abortControllerRef.current = null
        void useUserStore.getState().fetchMe()
      }
    },
    [
      sessionId,
      addStreamingPlaceholder,
      updateStreamingMessage,
      resetStreamingState,
      setStreaming,
      setStatus,
      appendStreamingContent,
      setSources,
      finalizeAssistantMessage,
      handleStreamError,
    ]
  )

  const sendMessage = useCallback(
    async (query: string) => {
      if (useChatStore.getState().isStreaming) return
      const userMessage: Message = {
        id: generateMessageId(),
        role: 'user',
        content: query,
        createdAt: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])
      await executeQueryStream(query)
    },
    [setMessages, executeQueryStream]
  )

  const retryMessage = useCallback(
    async (query: string, erroredMessageId: string) => {
      if (useChatStore.getState().isStreaming) return
      setMessages((prev) => prev.filter((msg) => msg.id !== erroredMessageId))
      await executeQueryStream(query)
    },
    [setMessages, executeQueryStream]
  )

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }, [])

  return { messages, sendMessage, cancelStream, retryMessage, loadFromHistory, clearMessages }
}

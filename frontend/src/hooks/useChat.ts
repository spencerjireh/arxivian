import { useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { streamChat, createStreamAbortController, StreamAbortError } from '../api/stream'
import { conversationKeys, confirmIngest } from '../api/conversations'
import { useChatStore } from '../stores/chatStore'
import { useSettingsStore, DEFAULT_SETTINGS } from '../stores/settingsStore'
import { useUserStore } from '../stores/userStore'
import { generateMessageId } from '../utils/id'
import { useMessageCache, chatKeys } from './useMessageCache'
import type {
  StreamRequest,
  Message,
  SourceInfo,
  MetadataEventData,
  ThinkingStep,
  CitationsEventData,
} from '../types/api'

export { chatKeys } from './useMessageCache'

type SettingKey = keyof StreamRequest & keyof typeof DEFAULT_SETTINGS

const SETTING_KEYS: readonly SettingKey[] = [
  'provider', 'model', 'temperature', 'top_k',
  'guardrail_threshold', 'max_retrieval_attempts', 'conversation_window',
] as const

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const abortControllerRef = useRef<AbortController | null>(null)
  const streamingMessageIdRef = useRef<string | null>(null)
  const hasAddedGeneratingStep = useRef(false)

  const { messages, setMessages, loadFromHistory, clearMessages } = useMessageCache(sessionId)

  // Get store actions (these are stable references)
  const setStreaming = useChatStore((s) => s.setStreaming)
  const appendStreamingContent = useChatStore((s) => s.appendStreamingContent)
  const setStatus = useChatStore((s) => s.setStatus)
  const setSources = useChatStore((s) => s.setSources)
  const setError = useChatStore((s) => s.setError)
  const addThinkingStep = useChatStore((s) => s.addThinkingStep)
  const addGeneratingStep = useChatStore((s) => s.addGeneratingStep)
  const completeGeneratingStep = useChatStore((s) => s.completeGeneratingStep)
  const getThinkingSteps = useChatStore((s) => s.getThinkingSteps)
  const setIngestProposal = useChatStore((s) => s.setIngestProposal)
  const setIsIngesting = useChatStore((s) => s.setIsIngesting)
  const clearIngestState = useChatStore((s) => s.clearIngestState)
  const resetStreamingState = useChatStore((s) => s.resetStreamingState)

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
      thinkingSteps: ThinkingStep[],
      citations?: CitationsEventData,
    ) => {
      const now = new Date()
      const finalizedSteps = thinkingSteps.map((step) => ({
        ...step,
        status: 'complete' as const,
        endTime: step.endTime ?? now,
      }))

      const assistantMessage: Message = {
        id: placeholderId || generateMessageId(),
        role: 'assistant',
        content,
        sources: sources.length > 0 ? sources : undefined,
        metadata,
        thinkingSteps: finalizedSteps.length > 0 ? finalizedSteps : undefined,
        citations,
        isStreaming: false,
        createdAt: new Date(),
      }

      if (metadata.session_id && sessionId === null) {
        const currentMessages = queryClient.getQueryData<Message[]>(chatKeys.messages(null)) ?? []

        const updatedMessages = currentMessages.map((msg) =>
          msg.id === placeholderId ? assistantMessage : msg
        )

        queryClient.setQueryData(chatKeys.messages(metadata.session_id), updatedMessages)
        queryClient.setQueryData(chatKeys.messages(null), [])
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })

        navigate(`/chat/${metadata.session_id}`, { replace: true })
      } else {
        setMessages((prev) => prev.map((msg) => (msg.id === placeholderId ? assistantMessage : msg)))
        queryClient.invalidateQueries({ queryKey: conversationKeys.lists() })
      }
    },
    [setMessages, sessionId, queryClient, navigate]
  )

  const buildStreamRequest = useCallback(
    (query: string): StreamRequest => {
      const settings = useSettingsStore.getState()
      const request: StreamRequest = {
        query,
        session_id: sessionId ?? undefined,
      }

      for (const key of SETTING_KEYS) {
        const value = settings[key]
        if (value !== DEFAULT_SETTINGS[key]) {
          Object.assign(request, { [key]: value })
        }
      }

      return request
    },
    [sessionId]
  )

  const sendMessage = useCallback(
    async (query: string) => {
      if (useChatStore.getState().isStreaming) {
        return
      }

      addUserMessage(query)
      resetStreamingState()
      hasAddedGeneratingStep.current = false
      setStreaming(true)
      setError(null)

      const streamingMessageId = addStreamingPlaceholder()
      streamingMessageIdRef.current = streamingMessageId

      abortControllerRef.current = createStreamAbortController()

      const request = buildStreamRequest(query)
      let accumulatedContent = ''
      let accumulatedSources: SourceInfo[] = []
      let accumulatedCitations: CitationsEventData | undefined

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
              if (!hasAddedGeneratingStep.current) {
                addGeneratingStep()
                hasAddedGeneratingStep.current = true
              }
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
              completeGeneratingStep()
              const finalThinkingSteps = getThinkingSteps()
              finalizeAssistantMessage(
                streamingMessageIdRef.current,
                accumulatedContent,
                accumulatedSources,
                data,
                finalThinkingSteps,
                accumulatedCitations,
              )
              streamingMessageIdRef.current = null
              setStreaming(false)
            },
            onError: (data) => {
              if (streamingMessageIdRef.current) {
                updateStreamingMessage(streamingMessageIdRef.current, {
                  isStreaming: false,
                  error: data.error,
                })
                streamingMessageIdRef.current = null
              }
              resetStreamingState()
              setError(data.error)
              setStreaming(false)
            },
            onCitations: (data) => {
              accumulatedCitations = data
              if (streamingMessageIdRef.current) {
                updateStreamingMessage(streamingMessageIdRef.current, { citations: data })
              }
            },
            onConfirmIngest: (data) => {
              setIngestProposal(data)
              addThinkingStep({
                step: 'confirming',
                message: 'Waiting for confirmation...',
                details: { papers: data.papers.length },
              })
              if (streamingMessageIdRef.current) {
                const currentSteps = getThinkingSteps()
                updateStreamingMessage(streamingMessageIdRef.current, {
                  ingestProposal: data,
                  thinkingSteps: currentSteps,
                })
              }
            },
            onIngestComplete: (data) => {
              setIsIngesting(false)
              addThinkingStep({
                step: 'ingesting',
                message: `Ingested ${data.papers_processed} papers`,
                details: {
                  papers_processed: data.papers_processed,
                  chunks_created: data.chunks_created,
                },
              })
              if (streamingMessageIdRef.current) {
                const currentSteps = getThinkingSteps()
                updateStreamingMessage(streamingMessageIdRef.current, {
                  thinkingSteps: currentSteps,
                  ingestResolved: true,
                })
              }
            },
            onDone: () => {
              setStatus(null)
            },
          },
          abortControllerRef.current
        )
      } catch (err) {
        if (err instanceof StreamAbortError) {
          if (streamingMessageIdRef.current) {
            setMessages((prev) => prev.filter((msg) => msg.id !== streamingMessageIdRef.current))
            streamingMessageIdRef.current = null
          }
          resetStreamingState()
          setStreaming(false)
          return
        }
        const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred'
        if (streamingMessageIdRef.current) {
          updateStreamingMessage(streamingMessageIdRef.current, {
            isStreaming: false,
            error: errorMessage,
          })
          streamingMessageIdRef.current = null
        }
        resetStreamingState()
        setError(errorMessage)
        setStreaming(false)
      } finally {
        abortControllerRef.current = null
        // Refresh user usage counts after stream completes
        useUserStore.getState().fetchMe()
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
      addGeneratingStep,
      completeGeneratingStep,
      getThinkingSteps,
      finalizeAssistantMessage,
      setMessages,
      setIngestProposal,
      setIsIngesting,
    ]
  )

  const handleIngestConfirmation = useCallback(
    async (approved: boolean, selectedIds: string[]) => {
      const proposal = useChatStore.getState().ingestProposal
      if (!proposal) return

      if (approved) {
        setIsIngesting(true)
        addThinkingStep({
          step: 'ingesting',
          message: `Adding ${selectedIds.length} papers...`,
          details: { count: selectedIds.length },
        })
        if (streamingMessageIdRef.current) {
          const currentSteps = getThinkingSteps()
          updateStreamingMessage(streamingMessageIdRef.current, {
            thinkingSteps: currentSteps,
          })
        }
      }

      try {
        await confirmIngest(proposal.session_id, approved, selectedIds)
      } catch (err) {
        console.error('Failed to confirm ingest:', err)
        clearIngestState()
      }
    },
    [
      setIsIngesting,
      addThinkingStep,
      getThinkingSteps,
      updateStreamingMessage,
      clearIngestState,
    ]
  )

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

  return {
    messages,
    sendMessage,
    cancelStream,
    handleIngestConfirmation,
    loadFromHistory,
    clearMessages,
  }
}

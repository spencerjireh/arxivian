// Zustand chat state store

import { create } from 'zustand'
import type {
  Message,
  SourceInfo,
  MetadataEventData,
  ConversationTurnResponse,
} from '../types/api'

interface ChatState {
  // State
  sessionId: string | null
  messages: Message[]
  isStreaming: boolean
  currentStatus: string | null
  streamingContent: string
  sources: SourceInfo[]
  error: string | null

  // Actions
  setSessionId: (id: string | null) => void
  addUserMessage: (content: string) => void
  startAssistantMessage: () => void
  appendToken: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  finalizeMessage: (metadata: MetadataEventData) => void
  setError: (error: string | null) => void
  loadHistory: (turns: ConversationTurnResponse[]) => void
  reset: () => void
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

const initialState = {
  sessionId: null,
  messages: [],
  isStreaming: false,
  currentStatus: null,
  streamingContent: '',
  sources: [],
  error: null,
}

export const useChatStore = create<ChatState>((set, get) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),

  addUserMessage: (content) => {
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      createdAt: new Date(),
    }
    set((state) => ({
      messages: [...state.messages, userMessage],
      error: null,
    }))
  },

  startAssistantMessage: () => {
    set({
      isStreaming: true,
      streamingContent: '',
      sources: [],
      error: null,
    })
  },

  appendToken: (token) => {
    set((state) => ({
      streamingContent: state.streamingContent + token,
    }))
  },

  setStatus: (status) => set({ currentStatus: status }),

  setSources: (sources) => set({ sources }),

  finalizeMessage: (metadata) => {
    const { streamingContent, sources } = get()
    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: streamingContent,
      sources: sources.length > 0 ? sources : undefined,
      metadata,
      createdAt: new Date(),
    }

    set((state) => ({
      messages: [...state.messages, assistantMessage],
      isStreaming: false,
      currentStatus: null,
      streamingContent: '',
      sources: [],
      sessionId: metadata.session_id || state.sessionId,
    }))
  },

  setError: (error) =>
    set({
      error,
      isStreaming: false,
      currentStatus: null,
    }),

  loadHistory: (turns) => {
    const messages: Message[] = turns.flatMap((turn) => [
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
    set({ messages })
  },

  reset: () => set(initialState),
}))

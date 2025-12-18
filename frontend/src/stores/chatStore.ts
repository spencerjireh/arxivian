// Zustand chat UI state store
// Only manages streaming/UI state - message data is in TanStack Query cache

import { create } from 'zustand'
import type { SourceInfo } from '../types/api'

interface ChatUIState {
  // Streaming state
  isStreaming: boolean
  streamingContent: string
  currentStatus: string | null
  sources: SourceInfo[]
  error: string | null

  // Actions
  setStreaming: (isStreaming: boolean) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  setError: (error: string | null) => void
  resetStreamingState: () => void
}

const initialStreamingState = {
  isStreaming: false,
  streamingContent: '',
  currentStatus: null,
  sources: [] as SourceInfo[],
  error: null,
}

export const useChatStore = create<ChatUIState>((set) => ({
  ...initialStreamingState,

  setStreaming: (isStreaming) => set({ isStreaming }),

  setStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingContent: (token) =>
    set((state) => ({
      streamingContent: state.streamingContent + token,
    })),

  setStatus: (status) => set({ currentStatus: status }),

  setSources: (sources) => set({ sources }),

  setError: (error) =>
    set({
      error,
      isStreaming: false,
      currentStatus: null,
    }),

  resetStreamingState: () => set(initialStreamingState),
}))

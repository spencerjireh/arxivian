// Zustand store for the streaming state of the one mounted chat surface.

import { create } from 'zustand'
import type { SourceInfo } from '../types/api'

interface ChatUIState {
  isStreaming: boolean
  streamingContent: string
  /** The latest STATUS message while a turn is in flight; null when idle. */
  currentStatus: string | null
  sources: SourceInfo[]

  setStreaming: (isStreaming: boolean) => void
  appendStreamingContent: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  resetStreamingState: () => void
}

const initialState = {
  isStreaming: false,
  streamingContent: '',
  currentStatus: null,
  sources: [] as SourceInfo[],
}

export const useChatStore = create<ChatUIState>((set) => ({
  ...initialState,
  setStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamingContent: (token) =>
    set((state) => ({ streamingContent: state.streamingContent + token })),
  setStatus: (status) => set({ currentStatus: status }),
  setSources: (sources) => set({ sources }),
  resetStreamingState: () => set(initialState),
}))

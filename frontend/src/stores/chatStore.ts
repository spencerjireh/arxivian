// Zustand store for the streaming state of the one mounted chat surface: whether a turn is in
// flight and its latest status line. The turn's content lives in the message cache.

import { create } from 'zustand'

interface ChatUIState {
  isStreaming: boolean
  /** The latest STATUS message while a turn is in flight; null when idle. */
  currentStatus: string | null

  setStreaming: (isStreaming: boolean) => void
  setStatus: (status: string | null) => void
  resetStreamingState: () => void
}

const initialState = {
  isStreaming: false,
  currentStatus: null,
}

export const useChatStore = create<ChatUIState>((set) => ({
  ...initialState,
  setStreaming: (isStreaming) => set({ isStreaming }),
  setStatus: (status) => set({ currentStatus: status }),
  resetStreamingState: () => set(initialState),
}))

// Zustand settings store with localStorage persistence

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LLMProvider } from '../types/api'

export interface SettingsState {
  // LLM Provider Settings
  provider?: LLMProvider
  model?: string

  // Agent Parameters
  temperature: number
  top_k: number
  guardrail_threshold: number
  max_retrieval_attempts: number
  conversation_window: number

  // Actions
  setProvider: (provider?: LLMProvider) => void
  setModel: (model?: string) => void
  setTemperature: (temperature: number) => void
  setTopK: (topK: number) => void
  setGuardrailThreshold: (threshold: number) => void
  setMaxRetrievalAttempts: (attempts: number) => void
  setConversationWindow: (window: number) => void
  resetToDefaults: () => void
}

// Default values matching backend schema
export const DEFAULT_SETTINGS = {
  provider: undefined,
  model: undefined,
  temperature: 0.3,
  top_k: 3,
  guardrail_threshold: 75,
  max_retrieval_attempts: 3,
  conversation_window: 5,
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,

      setProvider: (provider) => set({ provider }),
      setModel: (model) => set({ model }),
      setTemperature: (temperature) => set({ temperature }),
      setTopK: (topK) => set({ top_k: topK }),
      setGuardrailThreshold: (threshold) => set({ guardrail_threshold: threshold }),
      setMaxRetrievalAttempts: (attempts) => set({ max_retrieval_attempts: attempts }),
      setConversationWindow: (window) => set({ conversation_window: window }),
      resetToDefaults: () => set(DEFAULT_SETTINGS),
    }),
    {
      name: 'chat-settings-storage',
    }
  )
)

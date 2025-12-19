// Zustand chat UI state store
// Only manages streaming/UI state - message data is in TanStack Query cache

import { create } from 'zustand'
import type { SourceInfo, ThinkingStep, ThinkingStepType, StatusEventData } from '../types/api'

interface ChatUIState {
  // Streaming state
  isStreaming: boolean
  streamingContent: string
  currentStatus: string | null
  sources: SourceInfo[]
  error: string | null

  // Thinking steps (accumulated during streaming)
  thinkingSteps: ThinkingStep[]

  // Actions
  setStreaming: (isStreaming: boolean) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  setError: (error: string | null) => void

  // Thinking step actions
  addThinkingStep: (data: StatusEventData) => void
  getThinkingSteps: () => ThinkingStep[]

  resetStreamingState: () => void
}

function generateStepId(): string {
  return `step-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

// Map backend step names to our types
function mapStepType(step: string): ThinkingStepType {
  switch (step) {
    case 'guardrail':
      return 'guardrail'
    case 'routing':
      return 'routing'
    case 'executing':
      return 'executing'
    case 'grading':
      return 'grading'
    case 'generation':
      return 'generation'
    case 'out_of_scope':
      return 'out_of_scope'
    default:
      return 'executing' // fallback
  }
}

// Check if a step message indicates completion
function isCompletionMessage(step: string, message: string): boolean {
  const completionPatterns: Record<string, RegExp[]> = {
    guardrail: [/is in scope/i, /is out of scope/i],
    routing: [/decided to/i],
    executing: [/executed/i, /tool completed/i, /tool failed/i],
    grading: [/found \d+ relevant/i],
    generation: [], // Generation doesn't really "complete" before content starts
  }

  const patterns = completionPatterns[step] || []
  return patterns.some((pattern) => pattern.test(message))
}

const initialStreamingState = {
  isStreaming: false,
  streamingContent: '',
  currentStatus: null,
  sources: [] as SourceInfo[],
  error: null,
  thinkingSteps: [] as ThinkingStep[],
}

export const useChatStore = create<ChatUIState>((set, get) => ({
  ...initialStreamingState,

  setStreaming: (isStreaming) => set({ isStreaming }),

  setStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingContent: (token) =>
    set((state) => ({
      streamingContent: state.streamingContent + token,
    })),

  setStatus: (status) => set({ currentStatus: status }),

  setSources: (sources) => set({ sources }),

  setError: (error) => set({ error }),

  addThinkingStep: (data: StatusEventData) => {
    const stepType = mapStepType(data.step)
    const isComplete = isCompletionMessage(data.step, data.message)

    set((state) => {
      // Check if we already have a running step of the same type
      const existingIndex = state.thinkingSteps.findIndex(
        (s) => s.step === stepType && s.status === 'running'
      )

      if (existingIndex !== -1) {
        // Update existing step
        const updatedSteps = [...state.thinkingSteps]
        updatedSteps[existingIndex] = {
          ...updatedSteps[existingIndex],
          message: data.message,
          details: data.details,
          status: isComplete ? 'complete' : 'running',
        }
        return { thinkingSteps: updatedSteps }
      } else {
        // Add new step
        const newStep: ThinkingStep = {
          id: generateStepId(),
          step: stepType,
          message: data.message,
          details: data.details,
          status: isComplete ? 'complete' : 'running',
          timestamp: new Date(),
        }
        return { thinkingSteps: [...state.thinkingSteps, newStep] }
      }
    })
  },

  getThinkingSteps: () => get().thinkingSteps,

  resetStreamingState: () => set(initialStreamingState),
}))

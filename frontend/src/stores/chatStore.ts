import { create } from 'zustand'
import type { SourceInfo, ThinkingStep, StatusEventData } from '../types/api'
import { STEP_ORDER } from '../types/api'
import { generateStepId } from '../utils/id'
import { calculateTotalDuration } from '../utils/duration'
import { mapStepType, isCompletionMessage } from '../lib/thinking'

interface ChatUIState {
  isStreaming: boolean
  streamingContent: string
  currentStatus: string | null
  sources: SourceInfo[]
  error: string | null
  thinkingSteps: ThinkingStep[]

  setStreaming: (isStreaming: boolean) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  setError: (error: string | null) => void

  addThinkingStep: (data: StatusEventData) => void
  getThinkingSteps: () => ThinkingStep[]
  getTotalDuration: () => number

  resetStreamingState: () => void
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
    const now = new Date()

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
          endTime: isComplete ? now : undefined,
        }
        return { thinkingSteps: updatedSteps }
      } else {
        // Add new step with timing info
        const newStep: ThinkingStep = {
          id: generateStepId(),
          step: stepType,
          message: data.message,
          details: data.details,
          status: isComplete ? 'complete' : 'running',
          timestamp: now,
          startTime: now,
          endTime: isComplete ? now : undefined,
          order: STEP_ORDER[stepType],
        }
        return { thinkingSteps: [...state.thinkingSteps, newStep] }
      }
    })
  },

  getThinkingSteps: () => get().thinkingSteps,

  getTotalDuration: () => calculateTotalDuration(get().thinkingSteps),

  resetStreamingState: () => set(initialStreamingState),
}))

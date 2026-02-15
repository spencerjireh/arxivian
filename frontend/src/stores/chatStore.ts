import { create } from 'zustand'
import type { SourceInfo, ThinkingStep, StatusEventData } from '../types/api'
import { STEP_CONFIG } from '../lib/thinking/constants'
import { generateStepId } from '../utils/id'
import { calculateTotalDuration } from '../utils/duration'
import { mapStepType, isCompletionMessage, isSkippableMessage, extractToolName } from '../lib/thinking'

function buildNewStep(
  stepType: ThinkingStep['step'],
  data: StatusEventData,
  isComplete: boolean,
  now: Date,
  toolName?: string,
): ThinkingStep {
  return {
    id: generateStepId(),
    step: stepType,
    message: data.message,
    details: data.details,
    status: isComplete ? 'complete' : 'running',
    timestamp: now,
    startTime: now,
    endTime: isComplete ? now : undefined,
    order: STEP_CONFIG[stepType].order,
    toolName,
  }
}

function applyStepUpdate(
  existing: ThinkingStep,
  data: StatusEventData,
  isComplete: boolean,
  now: Date,
): ThinkingStep {
  return {
    ...existing,
    message: data.message,
    details: data.details,
    status: isComplete ? 'complete' : 'running',
    endTime: isComplete ? now : undefined,
  }
}

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

    // Skip redundant chain_start/chain_end messages for executing steps
    if (isSkippableMessage(data.step, data.message)) return

    const isComplete = isCompletionMessage(stepType, data.message)
    const toolName = (data.details?.tool_name as string | undefined) ?? extractToolName(data.message)
    const now = new Date()

    set((state) => {
      const findPredicate = (s: ThinkingStep) =>
        stepType === 'executing' && toolName
          ? s.step === 'executing' && s.status === 'running' && s.toolName === toolName
          : s.step === stepType && s.status === 'running'

      const existingIndex = state.thinkingSteps.findIndex(findPredicate)

      if (existingIndex !== -1) {
        const updatedSteps = [...state.thinkingSteps]
        updatedSteps[existingIndex] = applyStepUpdate(
          updatedSteps[existingIndex], data, isComplete, now,
        )
        return { thinkingSteps: updatedSteps }
      }

      return {
        thinkingSteps: [
          ...state.thinkingSteps,
          buildNewStep(stepType, data, isComplete, now, toolName),
        ],
      }
    })
  },

  getThinkingSteps: () => get().thinkingSteps,

  getTotalDuration: () => calculateTotalDuration(get().thinkingSteps),

  resetStreamingState: () => set(initialStreamingState),
}))

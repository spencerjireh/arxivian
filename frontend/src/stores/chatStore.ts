import { create } from 'zustand'
import type {
  SourceInfo,
  ThinkingStep,
  StatusEventData,
  ActivityStep,
  ConfirmIngestEventData,
} from '../types/api'
import { generateStepId } from '../utils/id'
import { calculateTotalDuration } from '../utils/duration'
import {
  isToolStartEvent,
  isToolEndEvent,
  isRetryEvent,
  createActivityStep,
  createInternalStep,
  createRefiningStep,
  buildToolEndMessage,
  isInternalStepName,
  isInternalCompletion,
} from '../lib/thinking'

interface ChatUIState {
  isStreaming: boolean
  streamingContent: string
  currentStatus: string | null
  sources: SourceInfo[]
  error: string | null
  thinkingSteps: ThinkingStep[]
  ingestProposal: ConfirmIngestEventData | null
  isIngesting: boolean

  setStreaming: (isStreaming: boolean) => void
  setStreamingContent: (content: string) => void
  appendStreamingContent: (token: string) => void
  setStatus: (status: string | null) => void
  setSources: (sources: SourceInfo[]) => void
  setError: (error: string | null) => void

  addThinkingStep: (data: StatusEventData) => void
  addGeneratingStep: () => void
  completeGeneratingStep: () => void
  getThinkingSteps: () => ThinkingStep[]
  getTotalDuration: () => number

  setIngestProposal: (proposal: ConfirmIngestEventData | null) => void
  setIsIngesting: (isIngesting: boolean) => void
  clearIngestState: () => void

  resetStreamingState: () => void
}

const initialStreamingState = {
  isStreaming: false,
  streamingContent: '',
  currentStatus: null,
  sources: [] as SourceInfo[],
  error: null,
  thinkingSteps: [] as ThinkingStep[],
  ingestProposal: null as ConfirmIngestEventData | null,
  isIngesting: false,
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
    const now = new Date()

    set((state) => {
      // tool_start -> always append a new ActivityStep
      if (isToolStartEvent(data)) {
        const newStep = createActivityStep(data)
        return { thinkingSteps: [...state.thinkingSteps, newStep] }
      }

      // tool_end -> find last running ActivityStep with matching toolName, update it
      if (isToolEndEvent(data)) {
        const toolName = (data.details?.tool_name as string) ?? ''
        const success = (data.details?.success as boolean) ?? true
        const resultSummary = data.details?.result_summary as string | undefined
        const updatedSteps = [...state.thinkingSteps]

        for (let i = updatedSteps.length - 1; i >= 0; i--) {
          const step = updatedSteps[i]
          if (!step.isInternal && step.status === 'running' && step.toolName === toolName) {
            updatedSteps[i] = {
              ...step,
              message: buildToolEndMessage(toolName, success, resultSummary),
              status: success ? 'complete' : 'error',
              endTime: now,
            }
            break
          }
        }

        return { thinkingSteps: updatedSteps }
      }

      // Retry detection -> append a "refining" step (immediately complete)
      if (isRetryEvent(data)) {
        return { thinkingSteps: [...state.thinkingSteps, createRefiningStep(data)] }
      }

      // Internal node events -> deduplicate by kind (update running -> complete)
      if (isInternalStepName(data.step)) {
        const isComplete = isInternalCompletion(data)
        const existingIndex = state.thinkingSteps.findIndex(
          (s) => s.isInternal && s.kind === data.step && s.status === 'running'
        )

        if (existingIndex !== -1) {
          const updatedSteps = [...state.thinkingSteps]
          const existing = updatedSteps[existingIndex]
          if (existing.isInternal) {
            updatedSteps[existingIndex] = {
              ...existing,
              message: data.message,
              details: data.details,
              status: isComplete ? 'complete' : 'running',
              endTime: isComplete ? now : undefined,
            }
          }
          return { thinkingSteps: updatedSteps }
        }

        const newStep = createInternalStep(data)
        return {
          thinkingSteps: [
            ...state.thinkingSteps,
            isComplete ? { ...newStep, status: 'complete' as const, endTime: now } : newStep,
          ],
        }
      }

      return state
    })
  },

  addGeneratingStep: () => {
    set((state) => {
      const alreadyExists = state.thinkingSteps.some(
        (s) => !s.isInternal && s.kind === 'generating'
      )
      if (alreadyExists) return state

      const step: ActivityStep = {
        id: generateStepId(),
        kind: 'generating',
        toolName: '',
        label: 'Generating answer',
        message: 'Generating answer...',
        status: 'running',
        startTime: new Date(),
        isInternal: false,
      }
      return { thinkingSteps: [...state.thinkingSteps, step] }
    })
  },

  completeGeneratingStep: () => {
    const now = new Date()
    set((state) => {
      const updatedSteps = state.thinkingSteps.map((step) => {
        if (!step.isInternal && step.kind === 'generating' && step.status === 'running') {
          return { ...step, status: 'complete' as const, message: 'Answer generated', endTime: now }
        }
        return step
      })
      return { thinkingSteps: updatedSteps }
    })
  },

  getThinkingSteps: () => get().thinkingSteps,

  getTotalDuration: () => calculateTotalDuration(get().thinkingSteps),

  setIngestProposal: (proposal) => set({ ingestProposal: proposal }),

  setIsIngesting: (isIngesting) => set({ isIngesting }),

  clearIngestState: () => set({ ingestProposal: null, isIngesting: false }),

  resetStreamingState: () => set(initialStreamingState),
}))

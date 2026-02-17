import { useChatStore } from '../../../src/stores/chatStore'
import type { StatusEventData } from '../../../src/types/api'

const initialState = () => ({
  isStreaming: false,
  streamingContent: '',
  currentStatus: null,
  sources: [],
  error: null,
  thinkingSteps: [],
})

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.setState(initialState())
  })

  describe('setters', () => {
    it('setStreaming updates isStreaming', () => {
      useChatStore.getState().setStreaming(true)
      expect(useChatStore.getState().isStreaming).toBe(true)
    })

    it('setStreamingContent updates streamingContent', () => {
      useChatStore.getState().setStreamingContent('hello')
      expect(useChatStore.getState().streamingContent).toBe('hello')
    })

    it('setStatus updates currentStatus', () => {
      useChatStore.getState().setStatus('processing')
      expect(useChatStore.getState().currentStatus).toBe('processing')
    })

    it('setSources updates sources', () => {
      const sources = [{ arxiv_id: '123', title: 'Test', authors: [], pdf_url: '', relevance_score: 0.9 }]
      useChatStore.getState().setSources(sources)
      expect(useChatStore.getState().sources).toEqual(sources)
    })

    it('setError updates error', () => {
      useChatStore.getState().setError('something broke')
      expect(useChatStore.getState().error).toBe('something broke')
    })
  })

  describe('appendStreamingContent', () => {
    it('concatenates tokens to existing content', () => {
      useChatStore.getState().setStreamingContent('hello')
      useChatStore.getState().appendStreamingContent(' world')
      expect(useChatStore.getState().streamingContent).toBe('hello world')
    })
  })

  describe('addThinkingStep', () => {
    it('adds a new internal step for guardrail events', () => {
      const data: StatusEventData = { step: 'guardrail', message: 'Checking scope' }
      useChatStore.getState().addThinkingStep(data)

      const steps = useChatStore.getState().thinkingSteps
      expect(steps).toHaveLength(1)
      expect(steps[0].isInternal).toBe(true)
      if (steps[0].isInternal) {
        expect(steps[0].kind).toBe('guardrail')
      }
      expect(steps[0].message).toBe('Checking scope')
      expect(steps[0].status).toBe('running')
      expect(steps[0].id).toMatch(/^step-/)
    })

    it('deduplicates running internal steps of the same kind', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Still checking...' })

      const steps = useChatStore.getState().thinkingSteps
      expect(steps).toHaveLength(1)
      expect(steps[0].message).toBe('Still checking...')
    })

    it('marks internal step as complete on completion message', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Query is in scope' })

      const steps = useChatStore.getState().thinkingSteps
      expect(steps[0].status).toBe('complete')
      expect(steps[0].endTime).toBeInstanceOf(Date)
    })

    it('adds separate steps for different internal step kinds', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'routing', message: 'Deciding route...' })

      expect(useChatStore.getState().thinkingSteps).toHaveLength(2)
    })

    describe('tool start/end events', () => {
      it('creates an ActivityStep on tool start', () => {
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'Calling retrieve_chunks...',
          details: { tool_name: 'retrieve_chunks' },
        })

        const steps = useChatStore.getState().thinkingSteps
        expect(steps).toHaveLength(1)
        expect(steps[0].isInternal).toBe(false)
        if (!steps[0].isInternal) {
          expect(steps[0].toolName).toBe('retrieve_chunks')
          expect(steps[0].kind).toBe('retrieve')
        }
        expect(steps[0].status).toBe('running')
      })

      it('creates separate ActivitySteps for different tools', () => {
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'Calling retrieve_chunks...',
          details: { tool_name: 'retrieve_chunks' },
        })
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'Calling arxiv_search...',
          details: { tool_name: 'arxiv_search' },
        })

        const steps = useChatStore.getState().thinkingSteps
        expect(steps).toHaveLength(2)
      })

      it('completes matching tool step on tool end', () => {
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'Calling retrieve_chunks...',
          details: { tool_name: 'retrieve_chunks' },
        })
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'Calling arxiv_search...',
          details: { tool_name: 'arxiv_search' },
        })
        useChatStore.getState().addThinkingStep({
          step: 'executing',
          message: 'retrieve_chunks completed',
          details: { tool_name: 'retrieve_chunks', success: true },
        })

        const steps = useChatStore.getState().thinkingSteps
        expect(steps).toHaveLength(2)
        const retrieve = steps.find((s) => !s.isInternal && s.toolName === 'retrieve_chunks')
        const search = steps.find((s) => !s.isInternal && s.toolName === 'arxiv_search')
        expect(retrieve?.status).toBe('complete')
        expect(search?.status).toBe('running')
      })
    })

    describe('retry detection', () => {
      it('appends a refining step on retry event', () => {
        useChatStore.getState().addThinkingStep({
          step: 'grading',
          message: 'Retrying with different query',
          details: { iteration: 2 },
        })

        const steps = useChatStore.getState().thinkingSteps
        expect(steps).toHaveLength(1)
        expect(steps[0].isInternal).toBe(false)
        if (!steps[0].isInternal) {
          expect(steps[0].kind).toBe('refining')
        }
        expect(steps[0].status).toBe('complete')
      })
    })
  })

  describe('addGeneratingStep', () => {
    it('adds a generating ActivityStep', () => {
      useChatStore.getState().addGeneratingStep()

      const steps = useChatStore.getState().thinkingSteps
      expect(steps).toHaveLength(1)
      expect(steps[0].isInternal).toBe(false)
      if (!steps[0].isInternal) {
        expect(steps[0].kind).toBe('generating')
      }
      expect(steps[0].status).toBe('running')
    })

    it('does not duplicate generating step', () => {
      useChatStore.getState().addGeneratingStep()
      useChatStore.getState().addGeneratingStep()

      expect(useChatStore.getState().thinkingSteps).toHaveLength(1)
    })
  })

  describe('completeGeneratingStep', () => {
    it('marks generating step as complete', () => {
      useChatStore.getState().addGeneratingStep()
      useChatStore.getState().completeGeneratingStep()

      const steps = useChatStore.getState().thinkingSteps
      expect(steps[0].status).toBe('complete')
      expect(steps[0].endTime).toBeInstanceOf(Date)
    })
  })

  describe('getThinkingSteps', () => {
    it('returns the current thinking steps', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'test' })
      const steps = useChatStore.getState().getThinkingSteps()
      expect(steps).toHaveLength(1)
    })
  })

  describe('getTotalDuration', () => {
    it('returns 0 when no steps exist', () => {
      expect(useChatStore.getState().getTotalDuration()).toBe(0)
    })
  })

  describe('resetStreamingState', () => {
    it('resets all streaming state to initial values', () => {
      useChatStore.getState().setStreaming(true)
      useChatStore.getState().setStreamingContent('some content')
      useChatStore.getState().setStatus('processing')
      useChatStore.getState().setError('error')
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'test' })

      useChatStore.getState().resetStreamingState()

      const state = useChatStore.getState()
      expect(state.isStreaming).toBe(false)
      expect(state.streamingContent).toBe('')
      expect(state.currentStatus).toBeNull()
      expect(state.sources).toEqual([])
      expect(state.error).toBeNull()
      expect(state.thinkingSteps).toEqual([])
    })
  })
})

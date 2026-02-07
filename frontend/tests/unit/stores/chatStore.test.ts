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
    it('adds a new thinking step', () => {
      const data: StatusEventData = { step: 'guardrail', message: 'Checking scope' }
      useChatStore.getState().addThinkingStep(data)

      const steps = useChatStore.getState().thinkingSteps
      expect(steps).toHaveLength(1)
      expect(steps[0].step).toBe('guardrail')
      expect(steps[0].message).toBe('Checking scope')
      expect(steps[0].status).toBe('running')
      expect(steps[0].id).toMatch(/^step-/)
    })

    it('updates an existing running step of the same type', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Still checking...' })

      const steps = useChatStore.getState().thinkingSteps
      expect(steps).toHaveLength(1)
      expect(steps[0].message).toBe('Still checking...')
    })

    it('marks step as complete on completion message', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Query is in scope' })

      const steps = useChatStore.getState().thinkingSteps
      expect(steps[0].status).toBe('complete')
      expect(steps[0].endTime).toBeInstanceOf(Date)
    })

    it('adds a separate step for a different type', () => {
      useChatStore.getState().addThinkingStep({ step: 'guardrail', message: 'Checking...' })
      useChatStore.getState().addThinkingStep({ step: 'routing', message: 'Deciding route...' })

      expect(useChatStore.getState().thinkingSteps).toHaveLength(2)
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

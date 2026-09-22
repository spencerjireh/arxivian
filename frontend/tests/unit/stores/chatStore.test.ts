import { useChatStore } from '@/stores/chatStore'

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.getState().resetStreamingState()
  })

  it('setStreaming updates isStreaming', () => {
    useChatStore.getState().setStreaming(true)
    expect(useChatStore.getState().isStreaming).toBe(true)
  })

  it('setStatus updates currentStatus', () => {
    useChatStore.getState().setStatus('Classifying query...')
    expect(useChatStore.getState().currentStatus).toBe('Classifying query...')
    useChatStore.getState().setStatus(null)
    expect(useChatStore.getState().currentStatus).toBeNull()
  })

  it('resetStreamingState restores the initial state', () => {
    useChatStore.getState().setStreaming(true)
    useChatStore.getState().setStatus('processing')

    useChatStore.getState().resetStreamingState()

    expect(useChatStore.getState()).toMatchObject({ isStreaming: false, currentStatus: null })
  })
})

import { useChatStore } from '../../../src/stores/chatStore'

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.getState().resetStreamingState()
  })

  it('setStreaming updates isStreaming', () => {
    useChatStore.getState().setStreaming(true)
    expect(useChatStore.getState().isStreaming).toBe(true)
  })

  it('appendStreamingContent concatenates tokens', () => {
    useChatStore.getState().appendStreamingContent('hello')
    useChatStore.getState().appendStreamingContent(' world')
    expect(useChatStore.getState().streamingContent).toBe('hello world')
  })

  it('setStatus updates currentStatus', () => {
    useChatStore.getState().setStatus('Classifying query...')
    expect(useChatStore.getState().currentStatus).toBe('Classifying query...')
    useChatStore.getState().setStatus(null)
    expect(useChatStore.getState().currentStatus).toBeNull()
  })

  it('setSources updates sources', () => {
    const sources = [{ arxiv_id: '123', title: 'Test', authors: [], pdf_url: '', relevance_score: 0.9 }]
    useChatStore.getState().setSources(sources)
    expect(useChatStore.getState().sources).toEqual(sources)
  })

  it('resetStreamingState restores the initial state', () => {
    useChatStore.getState().setStreaming(true)
    useChatStore.getState().appendStreamingContent('some content')
    useChatStore.getState().setStatus('processing')
    useChatStore.getState().setSources([{ arxiv_id: '1', title: 't', authors: [], pdf_url: '', relevance_score: 1 }])

    useChatStore.getState().resetStreamingState()

    expect(useChatStore.getState()).toMatchObject({
      isStreaming: false,
      streamingContent: '',
      currentStatus: null,
      sources: [],
    })
  })
})

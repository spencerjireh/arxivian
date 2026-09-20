import { renderHook, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useChat, chatKeys } from '../../../src/hooks/useChat'
import { useChatStore } from '../../../src/stores/chatStore'
import type { ReactNode } from 'react'
import type { StreamCallbacks } from '../../../src/api/stream'
import type { Message, StreamRequest } from '../../../src/types/api'

const streamChat = vi.fn()
vi.mock('../../../src/api/stream', () => ({
  streamChat: (...args: unknown[]) => streamChat(...args),
  StreamAbortError: class extends Error {},
  StreamError: class extends Error {
    code = 'X'
  },
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }))
vi.mock('../../../src/stores/userStore', () => ({
  useUserStore: { getState: () => ({ fetchMe: vi.fn() }) },
}))

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

function completeStream(request: StreamRequest, callbacks: StreamCallbacks) {
  callbacks.onStatus?.({ step: 'classifying', message: 'Classifying query...' })
  callbacks.onContent?.({ token: 'Hi' })
  callbacks.onSources?.({
    sources: [
      { arxiv_id: request.arxiv_id, title: 'T', authors: [], pdf_url: '', relevance_score: 1 },
    ],
  })
  callbacks.onMetadata?.({
    session_id: 's-new',
    query: request.query,
    execution_time_ms: 1,
    retrieval_attempts: 1,
    turn_number: 0,
  })
  callbacks.onDone?.()
  return Promise.resolve()
}

beforeEach(() => {
  streamChat.mockReset()
  useChatStore.getState().resetStreamingState()
})

describe('useChat (paper-scoped)', () => {
  it('sends only query/arxiv_id/session_id, moves the draft, calls onSessionCreated', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const onSessionCreated = vi.fn()
    streamChat.mockImplementation(completeStream)

    const { result } = renderHook(
      () => useChat(null, { arxivId: '2401.00001', onSessionCreated }),
      { wrapper: makeWrapper(queryClient) }
    )

    await act(async () => {
      await result.current.sendMessage('explain')
    })

    const [request] = streamChat.mock.calls[0]
    expect(request).toEqual({ query: 'explain', arxiv_id: '2401.00001', session_id: undefined })
    expect(onSessionCreated).toHaveBeenCalledWith('s-new')

    const moved = queryClient.getQueryData<Message[]>(chatKeys.messages('s-new')) ?? []
    expect(moved.map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(moved[1].sources).toHaveLength(1)
    expect(moved[1].isStreaming).toBe(false)
    expect(queryClient.getQueryData<Message[]>(chatKeys.messages(null, '2401.00001'))).toEqual([])
    expect(useChatStore.getState().isStreaming).toBe(false)
    expect(useChatStore.getState().currentStatus).toBeNull()
  })

  it('a follow-up carries the session id and stays under it', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    // An existing thread has its history in the cache already (loaded by the panel).
    queryClient.setQueryData(chatKeys.messages('s-new'), [])
    streamChat.mockImplementation(completeStream)

    const { result } = renderHook(() => useChat('s-new', { arxivId: '2401.00001' }), {
      wrapper: makeWrapper(queryClient),
    })
    await act(async () => {
      await result.current.sendMessage('more')
    })

    expect(streamChat.mock.calls[0][0].session_id).toBe('s-new')
    const messages = queryClient.getQueryData<Message[]>(chatKeys.messages('s-new')) ?? []
    expect(messages).toHaveLength(2)
  })

  it('an inline error keeps the placeholder with the error attached', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    queryClient.setQueryData(chatKeys.messages('s1'), [])
    streamChat.mockImplementation((_req: StreamRequest, callbacks: StreamCallbacks) => {
      callbacks.onError?.({ error: 'Timed out', code: 'TIMEOUT' })
      return Promise.resolve()
    })

    const { result } = renderHook(() => useChat('s1', { arxivId: '2401.00001' }), {
      wrapper: makeWrapper(queryClient),
    })
    await act(async () => {
      await result.current.sendMessage('q')
    })

    const messages = queryClient.getQueryData<Message[]>(chatKeys.messages('s1')) ?? []
    expect(messages[1].error).toEqual({ message: 'Timed out', code: 'TIMEOUT' })
    expect(messages[1].isStreaming).toBe(false)
  })

  it('draft keys are per paper', () => {
    expect(chatKeys.messages(null, 'x')).toEqual(['chat', 'messages', null, 'x'])
    expect(chatKeys.messages('s1', 'x')).toEqual(['chat', 'messages', 's1'])
  })
})

import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useChat, chatKeys } from '@/features/paper/hooks/useChat'
import { meKeys } from '@/lib/auth'
import { useChatStore } from '@/stores/chatStore'
import type { ReactNode } from 'react'
import type { StreamCallbacks } from '@/features/paper/api/stream-chat'
import type { ConversationTurn, Message, StreamRequest } from '@/types/api'

const streamChat = vi.fn()
vi.mock('@/features/paper/api/stream-chat', () => ({
  streamChat: (...args: unknown[]) => streamChat(...args),
  StreamAbortError: class extends Error {},
  StreamError: class extends Error {
    code = 'X'
  },
}))
vi.mock('@/lib/notifications', () => ({ notify: { error: vi.fn() } }))
const fetchConversation = vi.fn()
vi.mock('@/features/paper/api/get-conversation', async () => ({
  ...(await vi.importActual<typeof import('@/features/paper/api/get-conversation')>(
    '@/features/paper/api/get-conversation'
  )),
  fetchConversation: (...args: unknown[]) => fetchConversation(...args),
}))

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
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

const turn: ConversationTurn = {
  turn_number: 1,
  user_query: 'earlier question',
  agent_response: 'earlier answer',
  provider: 'openai',
  model: 'gpt-5-nano',
  retrieval_attempts: 1,
  created_at: '2026-08-03T00:00:00Z',
}

beforeEach(() => {
  streamChat.mockReset()
  fetchConversation.mockReset()
  useChatStore.getState().resetStreamingState()
})

describe('useChat (paper-scoped)', () => {
  it('sends only query/arxiv_id/session_id, moves the draft, calls onSessionCreated', async () => {
    const queryClient = makeClient()
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
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
    // The turn counted against today's quota.
    expect(invalidate).toHaveBeenCalledWith({ queryKey: meKeys.me() })
    expect(fetchConversation).not.toHaveBeenCalled()
  })

  it('remounting under the new session id keeps the moved messages without a fetch', async () => {
    const queryClient = makeClient()
    streamChat.mockImplementation(completeStream)
    let sessionId: string | null = null
    const { result, rerender } = renderHook(
      () =>
        useChat(sessionId, {
          arxivId: '2401.00001',
          onSessionCreated: (id) => {
            sessionId = id
          },
        }),
      { wrapper: makeWrapper(queryClient) }
    )

    await act(async () => {
      await result.current.sendMessage('explain')
    })
    rerender()

    expect(result.current.isLoadingHistory).toBe(false)
    expect(result.current.messages.map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(fetchConversation).not.toHaveBeenCalled()
  })

  it('a real session id with an empty cache fetches the thread and maps its turns', async () => {
    const queryClient = makeClient()
    fetchConversation.mockResolvedValue({
      session_id: 's-old',
      created_at: '',
      updated_at: '',
      turns: [turn],
    })

    const { result } = renderHook(() => useChat('s-old', { arxivId: '2401.00001' }), {
      wrapper: makeWrapper(queryClient),
    })

    expect(result.current.isLoadingHistory).toBe(true)
    await waitFor(() => expect(result.current.isLoadingHistory).toBe(false))
    expect(fetchConversation).toHaveBeenCalledWith('s-old')
    expect(result.current.messages.map((m) => [m.role, m.content])).toEqual([
      ['user', 'earlier question'],
      ['assistant', 'earlier answer'],
    ])
  })

  it('a follow-up carries the session id and stays under it', async () => {
    const queryClient = makeClient()
    // An existing thread has its history in the cache already.
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
    expect(fetchConversation).not.toHaveBeenCalled()
  })

  it('an inline error keeps the placeholder with the error attached', async () => {
    const queryClient = makeClient()
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

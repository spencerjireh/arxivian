import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { useChat, chatKeys } from '../../../src/hooks/useChat'
import { useChatStore } from '../../../src/stores/chatStore'
import type { StreamCallbacks } from '../../../src/api/stream'
import type { Message, StreamRequest } from '../../../src/types/api'

const streamChat = vi.fn()
vi.mock('../../../src/api/stream', () => ({
  streamChat: (...args: unknown[]) => streamChat(...args),
  createStreamAbortController: () => new AbortController(),
  StreamAbortError: class extends Error {},
  StreamError: class extends Error {
    code = 'X'
  },
}))
vi.mock('sonner', () => ({ toast: { error: vi.fn() } }))
vi.mock('../../../src/stores/userStore', () => ({
  useUserStore: { getState: () => ({ fetchMe: vi.fn() }) },
}))

let lastPath = ''
function LocationProbe() {
  const { pathname } = useLocation()
  useEffect(() => {
    lastPath = pathname
  }, [pathname])
  return null
}

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/papers/2401.00001']}>
          <Routes>
            <Route path="*" element={<>{children}<LocationProbe /></>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
}

function completeStream(request: StreamRequest, callbacks: StreamCallbacks) {
  callbacks.onContent?.({ token: 'Hi' })
  callbacks.onMetadata?.({
    session_id: 's-new',
    query: request.query ?? '',
    execution_time_ms: 1,
    retrieval_attempts: 1,
    guardrail_passed: true,
    reasoning_steps: [],
  } as never)
  callbacks.onDone?.()
  return Promise.resolve()
}

beforeEach(() => {
  streamChat.mockReset()
  useChatStore.getState().resetStreamingState()
  useChatStore.getState().setStreaming(false)
})

describe('useChat scoped', () => {
  it('sends arxiv_id, keeps a scoped draft key, and calls onSessionCreated instead of navigating', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const onSessionCreated = vi.fn()
    streamChat.mockImplementation(completeStream)

    const { result } = renderHook(() => useChat(null, { arxivId: '2401.00001', onSessionCreated }), {
      wrapper: makeWrapper(queryClient),
    })

    await act(async () => {
      await result.current.sendMessage('explain')
    })

    const [request] = streamChat.mock.calls[0]
    expect(request).toMatchObject({ query: 'explain', arxiv_id: '2401.00001' })
    expect(onSessionCreated).toHaveBeenCalledWith('s-new')
    expect(lastPath).toBe('/papers/2401.00001')

    const moved = queryClient.getQueryData<Message[]>(chatKeys.messages('s-new')) ?? []
    expect(moved.map((m) => m.role)).toEqual(['user', 'assistant'])
    expect(queryClient.getQueryData<Message[]>(chatKeys.messages(null, '2401.00001'))).toEqual([])
    expect(queryClient.getQueryData<Message[]>(chatKeys.messages(null))).toBeUndefined()
  })

  it('unscoped: no arxiv_id and navigates to /chat/:id', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    streamChat.mockImplementation(completeStream)

    const { result } = renderHook(() => useChat(null), { wrapper: makeWrapper(queryClient) })
    await act(async () => {
      await result.current.sendMessage('hello')
    })

    const [request] = streamChat.mock.calls[0]
    expect(request.arxiv_id).toBeUndefined()
    await waitFor(() => expect(lastPath).toBe('/chat/s-new'))
  })

  it('scoped and unscoped drafts use distinct cache keys', () => {
    expect(chatKeys.messages(null, 'x')).toEqual(['chat', 'messages', null, 'x'])
    expect(chatKeys.messages(null)).toEqual(['chat', 'messages', null])
    expect(chatKeys.messages('s1', 'x')).toEqual(['chat', 'messages', 's1'])
  })
})

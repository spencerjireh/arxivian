import { screen, fireEvent } from '@testing-library/react'
import ScopedChatPanel from '@/features/paper/components/ScopedChatPanel'
import { renderWithProviders } from '../../../../helpers/renderWithProviders'

vi.mock('framer-motion', () => import('../../../../mocks/framer-motion'))

const sendMessage = vi.fn()
const cancelStream = vi.fn()
const clearMessages = vi.fn()
let messages: unknown[] = []
const useChatMock = vi.fn()

vi.mock('@/features/paper/hooks/useChat', () => ({
  useChat: (...args: unknown[]) => {
    useChatMock(...args)
    return {
      messages,
      sendMessage,
      cancelStream,
      retryMessage: vi.fn(),
      loadFromHistory: vi.fn(),
      clearMessages,
    }
  },
}))
vi.mock('@/features/paper/api/get-conversation', () => ({
  usePaperConversations: () => ({
    data: {
      total: 1,
      offset: 0,
      limit: 30,
      conversations: [
        {
          session_id: 's1',
          title: 'Earlier thread',
          turn_count: 2,
          created_at: '',
          updated_at: '',
        },
      ],
    },
  }),
  useConversation: () => ({ data: undefined }),
}))

beforeEach(() => {
  messages = []
  sendMessage.mockClear()
  cancelStream.mockClear()
  useChatMock.mockClear()
})

describe('ScopedChatPanel', () => {
  it('passes the scope to useChat and seeds prompts that send immediately', () => {
    const onSessionChange = vi.fn()
    renderWithProviders(
      <ScopedChatPanel
        arxivId="2401.00001"
        paperTitle="T"
        sessionId={null}
        onSessionChange={onSessionChange}
      />
    )
    expect(useChatMock).toHaveBeenCalledWith(
      null,
      expect.objectContaining({ arxivId: '2401.00001', onSessionCreated: onSessionChange })
    )
    fireEvent.click(screen.getByRole('button', { name: /Explain the core method/ }))
    expect(sendMessage).toHaveBeenCalledWith('Explain the core method of this paper.')
    expect(screen.getByRole('button', { name: /minimal repo/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /risky parts/ })).toBeInTheDocument()
  })

  it('switches threads through the picker and aborts the stream on unmount', () => {
    const onSessionChange = vi.fn()
    const { unmount } = renderWithProviders(
      <ScopedChatPanel
        arxivId="2401.00001"
        paperTitle="T"
        sessionId="s1"
        onSessionChange={onSessionChange}
      />
    )
    fireEvent.change(screen.getByLabelText('Thread'), { target: { value: '' } })
    expect(onSessionChange).toHaveBeenCalledWith(null)
    fireEvent.click(screen.getByRole('button', { name: 'New' }))
    expect(clearMessages).toHaveBeenCalled()
    unmount()
    expect(cancelStream).toHaveBeenCalled()
  })

  it('renders messages instead of prompts when the thread has content', () => {
    messages = [{ id: 'u1', role: 'user', content: 'What is it?', createdAt: new Date() }]
    renderWithProviders(
      <ScopedChatPanel
        arxivId="2401.00001"
        paperTitle="T"
        sessionId="s1"
        onSessionChange={vi.fn()}
      />
    )
    expect(screen.getByText('What is it?')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Explain the core method/ })
    ).not.toBeInTheDocument()
  })
})

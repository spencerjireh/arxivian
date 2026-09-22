import { screen } from '@testing-library/react'
import ChatMessage from '@/features/paper/components/chat/ChatMessage'
import { useChatStore } from '@/stores/chatStore'
import { renderWithProviders } from '../../../../../helpers/renderWithProviders'
import type { Message } from '@/types/api'

vi.mock('framer-motion', () => import('../../../../../mocks/framer-motion'))
vi.mock('@/features/paper/components/chat/MarkdownRenderer', () => ({
  default: ({ content }: { content: string }) => <div>{content}</div>,
}))

const assistant = (overrides: Partial<Message> = {}): Message => ({
  id: 'a1',
  role: 'assistant',
  content: '',
  createdAt: new Date(),
  ...overrides,
})

describe('ChatMessage', () => {
  beforeEach(() => useChatStore.getState().resetStreamingState())

  it('shows the current status line while streaming with no content yet', () => {
    useChatStore.getState().setStatus('Classifying query...')
    renderWithProviders(<ChatMessage message={assistant({ isStreaming: true })} isStreaming />)
    expect(screen.getByRole('status')).toHaveTextContent('Classifying query...')
  })

  it('hides the status line once tokens arrive', () => {
    useChatStore.getState().setStatus('Generating answer...')
    renderWithProviders(
      <ChatMessage message={assistant({ content: 'Hello', isStreaming: true })} isStreaming />
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('labels an answer without sources or citations as general knowledge', () => {
    renderWithProviders(<ChatMessage message={assistant({ content: 'Answer' })} />)
    expect(screen.getByText('Answered from general knowledge')).toBeInTheDocument()
  })
})

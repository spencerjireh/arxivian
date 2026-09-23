// Scoped chat: the turn list with auto-scroll and retry on a failed turn.
import { useAutoScroll } from '@/features/paper/hooks/useAutoScroll'
import ChatMessage from './ChatMessage'
import type { Message } from '@/types/api'

interface ChatMessagesProps {
  messages: Message[]
  onRetry?: (query: string, erroredMessageId: string) => void
  /** Tight padding for an embedded panel (no floating input to reserve space for). */
  compact?: boolean
}

export default function ChatMessages({ messages, onRetry, compact = false }: ChatMessagesProps) {
  const scrollRef = useAutoScroll(messages)

  // Empty state is now handled by EmptyConversationState in ChatPage
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {/* pb-48: reserves space for the absolutely-positioned ChatInput + settings drawer (see ChatPage.tsx) */}
      <div
        className={
          compact ? 'space-y-4 px-4 pt-4 pb-6' : 'mx-auto max-w-5xl space-y-6 px-6 pt-8 pb-48'
        }
      >
        {messages.map((message, index) => {
          // For errored assistant messages, find the preceding user query for retry
          let retryQuery: string | undefined
          if (message.role === 'assistant' && message.error) {
            for (let i = index - 1; i >= 0; i--) {
              if (messages[i].role === 'user') {
                retryQuery = messages[i].content
                break
              }
            }
          }

          return (
            <div key={message.id}>
              <ChatMessage
                message={message}
                isStreaming={message.isStreaming}
                onRetry={onRetry}
                retryQuery={retryQuery}
              />
            </div>
          )
        })}

        <div ref={scrollRef} />
      </div>
    </div>
  )
}

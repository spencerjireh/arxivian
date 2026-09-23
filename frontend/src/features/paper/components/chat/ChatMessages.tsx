// Scoped chat: the turn list with auto-scroll and retry on a failed turn.
import { useAutoScroll } from '@/features/paper/hooks/useAutoScroll'
import ChatMessage from './ChatMessage'
import type { Message } from '@/types/api'

interface ChatMessagesProps {
  messages: Message[]
  onRetry?: (query: string, erroredMessageId: string) => void
}

/** The empty state (seeded prompts) is the panel's job; this renders nothing for no turns. */
export default function ChatMessages({ messages, onRetry }: ChatMessagesProps) {
  const scrollRef = useAutoScroll(messages)

  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="space-y-4 px-4 pt-4 pb-6">
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

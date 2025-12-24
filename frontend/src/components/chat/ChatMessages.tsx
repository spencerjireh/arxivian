import type { Message } from '../../types/api'
import ChatMessage from './ChatMessage'
import { useAutoScroll } from '../../hooks/useAutoScroll'

interface ChatMessagesProps {
  messages: Message[]
}

export default function ChatMessages({ messages }: ChatMessagesProps) {
  const scrollRef = useAutoScroll(messages)

  // Empty state is now handled by EmptyConversationState in ChatPage
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {messages.map((message, index) => (
          <div key={message.id}>
            <ChatMessage
              message={message}
              isStreaming={message.isStreaming}
              isFirst={index === 0}
            />
          </div>
        ))}

        <div ref={scrollRef} />
      </div>
    </div>
  )
}

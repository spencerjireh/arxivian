import type { Message } from '../../types/api'
import ChatMessage from './ChatMessage'
import { useAutoScroll } from '../../hooks/useAutoScroll'

interface ChatMessagesProps {
  messages: Message[]
  onIngestConfirm?: (approved: boolean, selectedIds: string[]) => void
}

export default function ChatMessages({ messages, onIngestConfirm }: ChatMessagesProps) {
  const scrollRef = useAutoScroll(messages)

  // Empty state is now handled by EmptyConversationState in ChatPage
  if (messages.length === 0) {
    return null
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {/* pb-48: reserves space for the absolutely-positioned ChatInput + settings drawer (see ChatPage.tsx) */}
      <div className="max-w-5xl mx-auto px-6 pt-8 pb-48 space-y-6">
        {messages.map((message, index) => (
          <div key={message.id}>
            <ChatMessage
              message={message}
              isStreaming={message.isStreaming}
              isFirst={index === 0}
              onIngestConfirm={onIngestConfirm}
            />
          </div>
        ))}

        <div ref={scrollRef} />
      </div>
    </div>
  )
}

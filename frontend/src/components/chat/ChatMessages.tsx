// Message list container component

import { useRef, useEffect } from 'react'
import { MessageSquare } from 'lucide-react'
import type { Message } from '../../types/api'
import { useChatStore } from '../../stores/chatStore'
import ChatMessage from './ChatMessage'

interface ChatMessagesProps {
  messages: Message[]
}

export default function ChatMessages({ messages }: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Subscribe directly to streaming state from Zustand store for real-time updates
  const isStreaming = useChatStore((state) => state.isStreaming)
  const streamingContent = useChatStore((state) => state.streamingContent)
  const sources = useChatStore((state) => state.sources)
  const thinkingSteps = useChatStore((state) => state.thinkingSteps)

  // Auto-scroll to bottom when new messages, streaming content, or thinking steps change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent, thinkingSteps])

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 rounded-2xl bg-stone-100 flex items-center justify-center mx-auto mb-6">
            <MessageSquare className="w-7 h-7 text-stone-400" strokeWidth={1.5} />
          </div>
          <h2 className="font-display text-xl text-stone-900 mb-2">
            Start a conversation
          </h2>
          <p className="text-stone-500 leading-relaxed">
            Ask questions about research papers. The agent will search the literature and provide grounded answers.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {messages.map((message, index) => (
          <ChatMessage
            key={message.id}
            message={message}
            isFirst={index === 0}
          />
        ))}

        {/* Streaming message */}
        {isStreaming && (
          <ChatMessage
            message={{
              id: 'streaming',
              role: 'assistant',
              content: streamingContent,
              sources: sources.length > 0 ? sources : undefined,
              createdAt: new Date(),
            }}
            isStreaming
            streamingContent={streamingContent}
            streamingThinkingSteps={thinkingSteps}
          />
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

// Message list container component

import { useRef, useEffect } from 'react'
import { useChatStore } from '../../stores/chatStore'
import ChatMessage from './ChatMessage'

export default function ChatMessages() {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, isStreaming, streamingContent, sources } = useChatStore()

  // Auto-scroll to bottom when new messages or streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-lg">Ask a question about the research papers</p>
          <p className="text-sm mt-1">Your conversation will appear here</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
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
        />
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}

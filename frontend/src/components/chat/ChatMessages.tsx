import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare } from 'lucide-react'
import type { Message } from '../../types/api'
import { useChatStore } from '../../stores/chatStore'
import ChatMessage from './ChatMessage'
import { staggerContainer, staggerItem, fadeIn, transitions } from '../../lib/animations'

interface ChatMessagesProps {
  messages: Message[]
}

export default function ChatMessages({ messages }: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevMessagesLengthRef = useRef(messages.length)
  const prevIsStreamingRef = useRef(false)

  const isStreaming = useChatStore((state) => state.isStreaming)
  const streamingContent = useChatStore((state) => state.streamingContent)
  const sources = useChatStore((state) => state.sources)
  const thinkingSteps = useChatStore((state) => state.thinkingSteps)

  // Only scroll when new messages are added or streaming starts
  // Avoid scrolling on every thinkingSteps/streamingContent update
  useEffect(() => {
    const messagesAdded = messages.length > prevMessagesLengthRef.current
    const streamingJustStarted = isStreaming && !prevIsStreamingRef.current

    if (messagesAdded || streamingJustStarted) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    prevMessagesLengthRef.current = messages.length
    prevIsStreamingRef.current = isStreaming
  }, [messages.length, isStreaming])

  if (messages.length === 0 && !isStreaming) {
    return (
      <motion.div
        className="flex-1 flex items-center justify-center px-6"
        variants={fadeIn}
        initial="initial"
        animate="animate"
        transition={transitions.base}
      >
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
      </motion.div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <motion.div
        className="max-w-5xl mx-auto px-6 py-8 space-y-6"
        variants={staggerContainer}
        initial="initial"
        animate="animate"
      >
        {messages.map((message, index) => (
          <motion.div key={message.id} variants={staggerItem} transition={transitions.fast}>
            <ChatMessage
              message={message}
              isFirst={index === 0}
            />
          </motion.div>
        ))}

        {isStreaming && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={transitions.fast}
          >
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
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </motion.div>
    </div>
  )
}

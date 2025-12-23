import { motion } from 'framer-motion'
import { MessageSquare } from 'lucide-react'
import type { Message } from '../../types/api'
import ChatMessage from './ChatMessage'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { fadeIn, transitions } from '../../lib/animations'

interface ChatMessagesProps {
  messages: Message[]
}

export default function ChatMessages({ messages }: ChatMessagesProps) {
  const scrollRef = useAutoScroll(messages)

  if (messages.length === 0) {
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

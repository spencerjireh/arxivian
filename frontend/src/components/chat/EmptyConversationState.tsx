import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import type { ChatOptions } from '../../hooks/useChat'
import { transitions } from '../../lib/animations'
import ChatInput from './ChatInput'
import SuggestionChips from './SuggestionChips'

interface EmptyConversationStateProps {
  onSend: (query: string, options: ChatOptions) => void
  isStreaming: boolean
  onCancel?: () => void
}

export default function EmptyConversationState({
  onSend,
  isStreaming,
  onCancel,
}: EmptyConversationStateProps) {
  const shouldReduceMotion = useReducedMotion()
  const [selectedPrompt, setSelectedPrompt] = useState<string>()

  const getStaggerDelay = (index: number) => (shouldReduceMotion ? 0 : 0.05 * index)

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
      <div className="w-full max-w-2xl flex flex-col items-center">
        {/* Icon */}
        <motion.div
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transitions.base, delay: getStaggerDelay(0) }}
          className="w-14 h-14 rounded-2xl bg-stone-900 flex items-center justify-center mb-6 shadow-lg opacity-0"
        >
          <Sparkles className="w-6 h-6 text-white" strokeWidth={1.5} />
        </motion.div>

        {/* Heading */}
        <motion.h1
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transitions.base, delay: getStaggerDelay(1) }}
          className="font-display text-3xl sm:text-4xl text-stone-900 mb-3 tracking-tight text-center opacity-0"
        >
          How can I help you today?
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transitions.base, delay: getStaggerDelay(2) }}
          className="text-stone-500 text-center mb-8 max-w-md leading-relaxed opacity-0"
        >
          Ask questions about research papers, explore academic literature, or discover new insights.
        </motion.p>

        {/* Centered Input */}
        <motion.div
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...transitions.base, delay: getStaggerDelay(3) }}
          className="w-full mb-8 opacity-0"
        >
          <ChatInput
            onSend={onSend}
            isStreaming={isStreaming}
            onCancel={onCancel}
            variant="centered"
            defaultValue={selectedPrompt}
          />
        </motion.div>

        {/* Suggestion Chips */}
        <SuggestionChips onSelect={setSelectedPrompt} />
      </div>
    </div>
  )
}

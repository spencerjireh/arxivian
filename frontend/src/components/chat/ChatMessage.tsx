import { useState, useRef, useEffect } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { User, Sparkles } from 'lucide-react'
import type { Message } from '../../types/api'
import SourceCard from './SourceCard'
import MetadataPanel from './MetadataPanel'
import MarkdownRenderer from './MarkdownRenderer'
import ThinkingTimeline from './ThinkingTimeline'
import { cursorTransitionVariants } from '../../lib/animations'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  isFirst?: boolean
}

export default function ChatMessage({
  message,
  isStreaming,
}: ChatMessageProps) {
  const isUser = message.role === 'user'
  const content = message.content
  const shouldReduceMotion = useReducedMotion()
  const thinkingSteps = message.thinkingSteps

  const [cursorPhase, setCursorPhase] = useState<'streaming' | 'complete'>('streaming')
  const prevIsStreaming = useRef(isStreaming)

  useEffect(() => {
    if (!isStreaming && prevIsStreaming.current) {
      // Use queueMicrotask to avoid synchronous setState in effect
      queueMicrotask(() => setCursorPhase('complete'))
      const timer = setTimeout(() => {
        setCursorPhase('streaming')
      }, shouldReduceMotion ? 0 : 400)
      return () => clearTimeout(timer)
    }
    if (isStreaming) {
      queueMicrotask(() => setCursorPhase('streaming'))
    }
    prevIsStreaming.current = isStreaming
  }, [isStreaming, shouldReduceMotion])

  const showCursor = isStreaming || cursorPhase === 'complete'

  return (
    <div className={isUser ? 'flex justify-end' : ''}>
      <div className={isUser ? 'max-w-[80%]' : ''}>
        <div className={`flex items-center gap-2.5 mb-3 ${isUser ? 'justify-end' : ''}`}>
          {isUser ? (
            <>
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-100">
                <User className="w-3.5 h-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </>
          ) : (
            <>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-900">
                <Sparkles className="w-3.5 h-3.5 text-white" strokeWidth={1.5} />
              </div>
              <span className="text-sm font-medium text-stone-500">Agent</span>
            </>
          )}
        </div>

        <div className={isUser ? 'pr-9 text-right' : 'pl-9'}>
          {!isUser && thinkingSteps && thinkingSteps.length > 0 && (
            <div className="mb-4">
              <ThinkingTimeline steps={thinkingSteps} isStreaming={isStreaming} />
            </div>
          )}

          <div className="text-stone-800">
            {isUser ? (
              <div className="whitespace-pre-wrap leading-relaxed">{content}</div>
            ) : (
              <div className="prose-stone">
                <MarkdownRenderer
                  content={content || ''}
                  streamingCursor={
                    showCursor ? (
                      <motion.span
                        variants={shouldReduceMotion ? {} : cursorTransitionVariants}
                        animate={cursorPhase}
                        className="inline-block w-0.5 h-5 ml-0.5 bg-stone-400 align-text-bottom"
                      />
                    ) : undefined
                  }
                />
              </div>
            )}
          </div>

          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-6 pt-6 border-t border-stone-100">
              <h4 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                Sources
              </h4>
              <div className="space-y-2">
                {message.sources.map((source) => (
                  <SourceCard key={source.arxiv_id} source={source} />
                ))}
              </div>
            </div>
          )}

          {!isUser && message.metadata && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <MetadataPanel metadata={message.metadata} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

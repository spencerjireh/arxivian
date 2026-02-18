import { useState, useRef, useEffect } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, Lightbulb, User } from 'lucide-react'
import logoIcon from '../../assets/logo-icon.png'
import clsx from 'clsx'
import type { Message } from '../../types/api'
import SourceCard from './SourceCard'
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

  const hasToolActivity = !isUser && thinkingSteps?.some((s) => !s.isInternal && s.kind !== 'generating')

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

  const showCursor = (isStreaming && !!content) || cursorPhase === 'complete'

  return (
    <div className={clsx(isUser && 'flex justify-end')}>
      <div className={clsx(isUser && 'max-w-[80%]')}>
        <div className={clsx('flex items-center gap-2.5 mb-3', isUser && 'justify-end')}>
          {isUser ? (
            <>
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-stone-100">
                <User className="w-3.5 h-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </>
          ) : (
            <>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-stone-100">
                <img src={logoIcon} alt="" className="w-4 h-4" aria-hidden="true" />
              </div>
              <span className="text-sm font-medium text-stone-500">Arxivian</span>
            </>
          )}
        </div>

        <div className={clsx(isUser ? 'pr-9 text-right' : 'pl-9')}>
          {!isUser && thinkingSteps && thinkingSteps.length > 0 && (
            <div className="mb-4">
              <ThinkingTimeline steps={thinkingSteps} isStreaming={isStreaming} metadata={message.metadata} />
            </div>
          )}

          {!isUser && !isStreaming && thinkingSteps && thinkingSteps.length > 0 && content && (
            <div className="thinking-divider">
              <div className="thinking-divider-line" />
              <div className="thinking-divider-diamond" />
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

          {!isUser && message.error && (
            <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{message.error}</span>
            </div>
          )}

          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-6 pt-6 border-t border-stone-100">
              <h4 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                Sources
              </h4>
              <div className="space-y-2">
                {message.sources.map((source, index) => (
                  <SourceCard key={`${source.arxiv_id}-${index}`} source={source} />
                ))}
              </div>
            </div>
          )}

          {!isUser && !isStreaming && !message.sources && !hasToolActivity && content && !message.error && (
            <div className="mt-4 flex items-center gap-2 text-xs text-stone-400">
              <Lightbulb className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span>Answered from general knowledge</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

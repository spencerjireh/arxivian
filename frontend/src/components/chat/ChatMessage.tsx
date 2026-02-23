import { useState, useRef, useEffect } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, Lightbulb, User } from 'lucide-react'
import logoIcon from '../../assets/logo-icon.png'
import clsx from 'clsx'
import { useChatStore } from '../../stores/chatStore'
import type { Message } from '../../types/api'
import SourcesSection from './SourcesSection'
import CitationTree from './CitationTree'
import MarkdownRenderer from './MarkdownRenderer'
import ThinkingTimeline from './ThinkingTimeline'
import IngestConfirmation from './IngestConfirmation'
import {
  cursorTransitionVariants,
  sourcesRevealContainer,
} from '../../lib/animations'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  isFirst?: boolean
}

export default function ChatMessage({
  message,
  isStreaming,
}: ChatMessageProps) {
  const hasProposal = !!message.ingestProposal
  const storeIsIngesting = useChatStore((s) => (hasProposal ? s.isIngesting : false))
  const isUser = message.role === 'user'
  const content = message.content
  const shouldReduceMotion = useReducedMotion()
  const thinkingSteps = message.thinkingSteps

  const hasToolActivity = !isUser && thinkingSteps?.some((s) => !s.isInternal && s.kind !== 'generating')

  const [cursorPhase, setCursorPhase] = useState<'streaming' | 'complete'>('streaming')
  const prevIsStreaming = useRef(isStreaming)

  // Defer footer (sources / general-knowledge label) until after streaming ends
  const [showFooter, setShowFooter] = useState(!isStreaming)

  useEffect(() => {
    const wasStreaming = prevIsStreaming.current
    prevIsStreaming.current = isStreaming

    if (!isStreaming && wasStreaming) {
      queueMicrotask(() => setCursorPhase('complete'))
      const cursorTimer = setTimeout(
        () => setCursorPhase('streaming'),
        shouldReduceMotion ? 0 : 400,
      )
      const footerTimer = setTimeout(
        () => setShowFooter(true),
        shouldReduceMotion ? 0 : 300,
      )
      return () => {
        clearTimeout(cursorTimer)
        clearTimeout(footerTimer)
      }
    }
    if (isStreaming) {
      queueMicrotask(() => setCursorPhase('streaming'))
      queueMicrotask(() => setShowFooter(false))
    }
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
              <div className="relative">
                <AnimatePresence>
                  {isStreaming && (
                    <motion.div
                      key="streaming-ring"
                      className="absolute inset-0"
                      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.85 }}
                      animate={shouldReduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1 }}
                      exit={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.9 }}
                      transition={
                        shouldReduceMotion
                          ? { duration: 0 }
                          : { duration: 0.4, ease: [0.4, 0, 0.2, 1] }
                      }
                    >
                      {shouldReduceMotion ? (
                        <div
                          className="absolute -inset-[3px] rounded-xl border-2 border-[#C2704A]"
                          style={{ boxShadow: '0 0 8px rgba(194, 112, 74, 0.3)' }}
                        />
                      ) : (
                        <>
                          {/* Diffuse ambient glow */}
                          <motion.div
                            className="absolute -inset-[6px] rounded-2xl blur-[4px] opacity-40"
                            style={{
                              background:
                                'conic-gradient(from 180deg, transparent 60%, #C2704A 78%, transparent 95%)',
                            }}
                            animate={{ rotate: 360 }}
                            transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
                          />
                          {/* Sharp primary arc */}
                          <motion.div
                            className="absolute -inset-[3px] rounded-xl"
                            style={{
                              background:
                                'conic-gradient(from 180deg, transparent 65%, #C2704A 82%, transparent 95%)',
                            }}
                            animate={{ rotate: 360 }}
                            transition={{ duration: 2.4, repeat: Infinity, ease: 'linear' }}
                          />
                        </>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center bg-stone-100 relative"
                  style={
                    isStreaming && !shouldReduceMotion
                      ? { boxShadow: '0 0 6px rgba(194, 112, 74, 0.15)' }
                      : undefined
                  }
                >
                  <img src={logoIcon} alt="" className="w-4 h-4" aria-hidden="true" />
                </div>
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

          {!isUser && message.ingestProposal && (
            <IngestConfirmation
              proposal={message.ingestProposal}
              isResolved={message.ingestResolved}
              isIngesting={storeIsIngesting}
              ingestDeclined={message.ingestDeclined}
            />
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

          {!isUser && message.citations && (
            <div className="mt-4">
              <CitationTree citations={message.citations} />
            </div>
          )}

          {!isUser && showFooter && message.sources && message.sources.length > 0 && (
            <motion.div
              variants={shouldReduceMotion ? undefined : sourcesRevealContainer}
              initial="initial"
              animate="animate"
            >
              <SourcesSection sources={message.sources} shouldReduceMotion={!!shouldReduceMotion} />
            </motion.div>
          )}

          {!isUser && showFooter && !message.sources && !hasToolActivity && content && !message.error && (
            <motion.div
              className="mt-4 flex items-center gap-2 text-xs text-stone-400"
              variants={shouldReduceMotion ? undefined : sourcesRevealContainer}
              initial="initial"
              animate="animate"
            >
              <Lightbulb className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span>Answered from general knowledge</span>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

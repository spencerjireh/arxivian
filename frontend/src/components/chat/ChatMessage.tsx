import { lazy, Suspense, useState, useRef, useEffect } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Lightbulb, User } from 'lucide-react'
import clsx from 'clsx'
import logoIcon from '../../assets/logo-icon.png'
import { useChatStore } from '../../stores/chatStore'
import { cursorTransitionVariants, sourcesRevealContainer } from '../../lib/animations'
import MarkdownRenderer from './MarkdownRenderer'
import MessageErrorDisplay from './MessageErrorDisplay'
import type { Message } from '../../types/api'

const SourcesSection = lazy(() => import('./SourcesSection'))
const CitationTree = lazy(() => import('./CitationTree'))

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  onRetry?: (query: string, erroredMessageId: string) => void
  retryQuery?: string
}

export default function ChatMessage({
  message,
  isStreaming,
  onRetry,
  retryQuery,
}: ChatMessageProps) {
  const isUser = message.role === 'user'
  const content = message.content
  const shouldReduceMotion = useReducedMotion()
  // One status line while the turn is in flight (replaces the thinking timeline).
  const currentStatus = useChatStore((s) => (isStreaming ? s.currentStatus : null))

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
        shouldReduceMotion ? 0 : 400
      )
      const footerTimer = setTimeout(() => setShowFooter(true), shouldReduceMotion ? 0 : 300)
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
        <div className={clsx('mb-3 flex items-center gap-2.5', isUser && 'justify-end')}>
          {isUser ? (
            <>
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                <User className="h-3.5 w-3.5 text-stone-500" strokeWidth={1.5} />
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
                            className="absolute -inset-[6px] rounded-2xl opacity-40 blur-[4px]"
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
                  className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100"
                  style={
                    isStreaming && !shouldReduceMotion
                      ? { boxShadow: '0 0 6px rgba(194, 112, 74, 0.15)' }
                      : undefined
                  }
                >
                  <img src={logoIcon} alt="" className="h-4 w-4" aria-hidden="true" />
                </div>
              </div>
              <span className="text-sm font-medium text-stone-500">Arxivian</span>
            </>
          )}
        </div>

        <div className={clsx(isUser ? 'pr-9 text-right' : 'pl-9')}>
          {!isUser && isStreaming && !content && currentStatus && (
            <p className="mb-3 text-xs text-stone-400" role="status" aria-live="polite">
              {currentStatus}
            </p>
          )}

          <div className="text-stone-800">
            {isUser ? (
              <div className="leading-relaxed whitespace-pre-wrap">{content}</div>
            ) : (
              <div className="prose-stone">
                <MarkdownRenderer
                  content={content || ''}
                  streamingCursor={
                    showCursor ? (
                      <motion.span
                        variants={shouldReduceMotion ? {} : cursorTransitionVariants}
                        animate={cursorPhase}
                        className="ml-0.5 inline-block h-5 w-0.5 bg-stone-400 align-text-bottom"
                      />
                    ) : undefined
                  }
                />
              </div>
            )}
          </div>

          {!isUser && message.error && (
            <MessageErrorDisplay
              error={message.error}
              onRetry={onRetry && ((query) => onRetry(query, message.id))}
              retryQuery={retryQuery}
            />
          )}

          {!isUser && message.citations && (
            <div className="mt-4">
              <Suspense fallback={null}>
                <CitationTree citations={message.citations} />
              </Suspense>
            </div>
          )}

          {!isUser && showFooter && message.sources && message.sources.length > 0 && (
            <motion.div
              variants={shouldReduceMotion ? undefined : sourcesRevealContainer}
              initial="initial"
              animate="animate"
            >
              <Suspense fallback={null}>
                <SourcesSection
                  sources={message.sources}
                  shouldReduceMotion={!!shouldReduceMotion}
                />
              </Suspense>
            </motion.div>
          )}

          {!isUser &&
            showFooter &&
            !message.sources &&
            !message.citations &&
            content &&
            !message.error && (
              <motion.div
                className="mt-4 flex items-center gap-2 text-xs text-stone-400"
                variants={shouldReduceMotion ? undefined : sourcesRevealContainer}
                initial="initial"
                animate="animate"
              >
                <Lightbulb className="h-3.5 w-3.5" strokeWidth={1.5} />
                <span>Answered from general knowledge</span>
              </motion.div>
            )}
        </div>
      </div>
    </div>
  )
}

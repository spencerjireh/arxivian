import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import clsx from 'clsx'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Settings2, X, ArrowUp, RotateCcw } from 'lucide-react'
import type { LLMProvider } from '../../types/api'
import { useSettingsStore } from '../../stores/settingsStore'
import { useUserStore } from '../../stores/userStore'
import { useChatStore } from '../../stores/chatStore'
import { transitions } from '../../lib/animations'
import Button from '../ui/Button'

interface ChatInputProps {
  onSend: (query: string) => void
  isStreaming: boolean
  onCancel?: () => void
  variant?: 'bottom' | 'centered'
  defaultValue?: string
}

export default function ChatInput({
  onSend,
  isStreaming,
  onCancel,
  variant = 'bottom',
  defaultValue,
}: ChatInputProps) {
  const [query, setQuery] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const [isOverflowing, setIsOverflowing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const shouldReduceMotion = useReducedMotion()

  // Derive query from defaultValue when it changes (React 18+ pattern)
  const [prevDefaultValue, setPrevDefaultValue] = useState(defaultValue)
  if (defaultValue !== prevDefaultValue) {
    setPrevDefaultValue(defaultValue)
    if (defaultValue !== undefined) {
      setQuery(defaultValue)
    }
  }

  // Focus textarea when defaultValue changes
  useEffect(() => {
    if (defaultValue) {
      textareaRef.current?.focus()
    }
  }, [defaultValue])

  const lineCount = query.split('\n').length
  const MAX_HEIGHT = 160
  const hasContent = query.trim().length > 0

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    const scrollHeight = textarea.scrollHeight
    const newHeight = Math.min(scrollHeight, MAX_HEIGHT)
    textarea.style.height = `${newHeight}px`
    setIsOverflowing(scrollHeight > MAX_HEIGHT)
  }, [query])

  // Close drawer on Escape
  useEffect(() => {
    if (!showAdvanced) return
    const handleEscape = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setShowAdvanced(false)
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [showAdvanced])

  const canAdjustSettings = useUserStore((s) => s.me?.can_adjust_settings ?? false)
  const isAwaitingConfirmation = useChatStore((s) => s.ingestProposal !== null)

  const {
    provider,
    model,
    temperature,
    top_k,
    guardrail_threshold,
    max_retrieval_attempts,
    conversation_window,
    setProvider,
    setModel,
    setTemperature,
    setTopK,
    setGuardrailThreshold,
    setMaxRetrievalAttempts,
    setConversationWindow,
    resetToDefaults,
  } = useSettingsStore()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || isStreaming || isAwaitingConfirmation) return

    onSend(query.trim())
    setQuery('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const isCentered = variant === 'centered'

  const buttonMotion = shouldReduceMotion
    ? { initial: false as const, exit: undefined, transition: { duration: 0 } }
    : { initial: { scale: 0.8, opacity: 0 }, exit: { scale: 0.8, opacity: 0 }, transition: transitions.fast }

  return (
    <div className={clsx(!isCentered && 'chat-input-fade relative z-10')}>
      <div className={clsx(isCentered ? 'max-w-2xl' : 'max-w-5xl', 'mx-auto px-6 py-4')}>
        <form onSubmit={handleSubmit} className="relative">
          {/* Settings slide-up drawer */}
          <AnimatePresence>
            {showAdvanced && (
              <>
                <motion.div
                  key="backdrop"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
                  onClick={() => setShowAdvanced(false)}
                  className="fixed inset-0 z-40"
                  aria-hidden="true"
                />
                <motion.div
                  key="drawer"
                  initial={shouldReduceMotion ? false : { y: 16, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={shouldReduceMotion ? { opacity: 0 } : { y: 16, opacity: 0 }}
                  transition={shouldReduceMotion ? { duration: 0 } : transitions.base}
                  className="absolute bottom-full left-0 right-0 z-50 mb-2"
                >
                  <div className="p-5 bg-white/95 backdrop-blur-sm rounded-xl border border-stone-200 shadow-lg">
                    <div className="flex items-center justify-between mb-5">
                      <h3 className="text-sm font-medium text-stone-700">
                        Advanced Settings
                      </h3>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={resetToDefaults}
                        leftIcon={<RotateCcw className="w-3 h-3" strokeWidth={1.5} />}
                      >
                        Reset
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-5">
                      {canAdjustSettings && (
                        <>
                          <div>
                            <label className="block text-xs text-stone-500 mb-1.5">
                              Provider
                            </label>
                            <select
                              value={provider ?? ''}
                              onChange={(e) =>
                                setProvider(
                                  (e.target.value || undefined) as LLMProvider | undefined
                                )
                              }
                              className="w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150"
                            >
                              <option value="">Default</option>
                              <option value="openai">OpenAI</option>
                              <option value="nvidia_nim">NVIDIA NIM</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-xs text-stone-500 mb-1.5">
                              Model
                            </label>
                            <input
                              type="text"
                              value={model ?? ''}
                              onChange={(e) => setModel(e.target.value || undefined)}
                              placeholder="Default"
                              className="w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150"
                            />
                          </div>
                        </>
                      )}

                      <div>
                        <label className="block text-xs text-stone-500 mb-1.5">
                          Temperature
                          <span className="float-right font-mono text-stone-400">
                            {temperature.toFixed(1)}
                          </span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.1"
                          value={temperature}
                          onChange={(e) => setTemperature(parseFloat(e.target.value))}
                          className="w-full"
                        />
                      </div>

                      <div>
                        <label className="block text-xs text-stone-500 mb-1.5">
                          Top K
                          <span className="float-right font-mono text-stone-400">
                            {top_k}
                          </span>
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="10"
                          step="1"
                          value={top_k}
                          onChange={(e) => setTopK(parseInt(e.target.value))}
                          className="w-full"
                        />
                      </div>

                      <div>
                        <label className="block text-xs text-stone-500 mb-1.5">
                          Guardrail
                          <span className="float-right font-mono text-stone-400">
                            {guardrail_threshold}%
                          </span>
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="5"
                          value={guardrail_threshold}
                          onChange={(e) => setGuardrailThreshold(parseInt(e.target.value))}
                          className="w-full"
                        />
                      </div>

                      <div>
                        <label className="block text-xs text-stone-500 mb-1.5">
                          Max Retrieval
                          <span className="float-right font-mono text-stone-400">
                            {max_retrieval_attempts}
                          </span>
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="5"
                          step="1"
                          value={max_retrieval_attempts}
                          onChange={(e) =>
                            setMaxRetrievalAttempts(parseInt(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>

                      <div>
                        <label className="block text-xs text-stone-500 mb-1.5">
                          Context Window
                          <span className="float-right font-mono text-stone-400">
                            {conversation_window}
                          </span>
                        </label>
                        <input
                          type="range"
                          min="1"
                          max="10"
                          step="1"
                          value={conversation_window}
                          onChange={(e) =>
                            setConversationWindow(parseInt(e.target.value))
                          }
                          className="w-full"
                        />
                      </div>
                    </div>
                  </div>
                </motion.div>
              </>
            )}
          </AnimatePresence>

          {/* Compound input container */}
          <div
            className={clsx(
              'rounded-xl border transition-[background-color,border-color,box-shadow] duration-200',
              hasContent || isFocused
                ? 'bg-white border-amber-700/25 shadow-sm'
                : 'bg-stone-50 border-stone-200',
            )}
          >
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask about research papers..."
              rows={1}
              disabled={isStreaming || isAwaitingConfirmation}
              className={clsx(
                'w-full px-4 pt-3 pb-1.5 text-stone-800 bg-transparent rounded-t-xl',
                'resize-none placeholder:text-stone-400 outline-none',
                'disabled:opacity-60 disabled:cursor-not-allowed',
                'transition-colors duration-200',
                isOverflowing
                  ? 'overflow-y-auto scrollbar-thin scrollbar-thumb-stone-300 scrollbar-track-transparent'
                  : 'overflow-hidden',
              )}
              style={{ minHeight: '36px', maxHeight: `${MAX_HEIGHT}px` }}
            />

            {/* Bottom toolbar */}
            <div className="flex items-center justify-between px-2.5 pb-2.5">
              <div className="flex items-center gap-2">
                {canAdjustSettings && (
                  <Button
                    type="button"
                    variant="icon"
                    size="sm"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className={clsx(showAdvanced && 'bg-stone-200 text-stone-700')}
                    aria-label="Advanced settings"
                  >
                    <Settings2 className="w-4 h-4" strokeWidth={1.5} />
                  </Button>
                )}
                {lineCount > 1 && (isFocused || query) && (
                  <span className="text-xs text-stone-400 pointer-events-none">
                    {lineCount} lines
                  </span>
                )}
              </div>

              {/* Send / Cancel morph */}
              <AnimatePresence mode="wait" initial={false}>
                {isStreaming ? (
                  <motion.button
                    key="cancel"
                    type="button"
                    onClick={onCancel}
                    {...buttonMotion}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-8 h-8 flex items-center justify-center bg-red-500 text-white hover:bg-red-600 rounded-lg transition-colors"
                    aria-label="Cancel"
                  >
                    <X className="w-4 h-4" strokeWidth={2} />
                  </motion.button>
                ) : (
                  <motion.button
                    key="send"
                    type="submit"
                    disabled={!hasContent}
                    {...buttonMotion}
                    animate={{ scale: 1, opacity: 1 }}
                    className="w-8 h-8 flex items-center justify-center bg-amber-700 text-white hover:bg-amber-800 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors"
                    aria-label="Send"
                  >
                    <ArrowUp className="w-4 h-4" strokeWidth={2} />
                  </motion.button>
                )}
              </AnimatePresence>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import clsx from 'clsx'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { X, ArrowUp } from 'lucide-react'
import { transitions } from '../../lib/animations'

interface ChatInputProps {
  onSend: (query: string) => void
  isStreaming: boolean
  onCancel?: () => void
  variant?: 'bottom' | 'centered'
  defaultValue?: string
}

const MAX_HEIGHT = 160

export default function ChatInput({
  onSend,
  isStreaming,
  onCancel,
  variant = 'bottom',
  defaultValue,
}: ChatInputProps) {
  const [query, setQuery] = useState('')
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

  useEffect(() => {
    if (defaultValue) {
      textareaRef.current?.focus()
    }
  }, [defaultValue])

  const lineCount = query.split('\n').length
  const hasContent = query.trim().length > 0

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    const scrollHeight = textarea.scrollHeight
    textarea.style.height = `${Math.min(scrollHeight, MAX_HEIGHT)}px`
    setIsOverflowing(scrollHeight > MAX_HEIGHT)
  }, [query])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim() || isStreaming) return
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
              placeholder="Ask about this paper..."
              rows={1}
              disabled={isStreaming}
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

            <div className="flex items-center justify-between px-2.5 pb-2.5">
              <div className="flex items-center gap-2">
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

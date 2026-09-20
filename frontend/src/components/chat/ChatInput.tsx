// Scoped chat: auto-growing textarea with submit and abort controls.
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
    : {
        initial: { scale: 0.8, opacity: 0 },
        exit: { scale: 0.8, opacity: 0 },
        transition: transitions.fast,
      }

  return (
    <div className={clsx(!isCentered && 'chat-input-fade relative z-10')}>
      <div className={clsx(isCentered ? 'max-w-2xl' : 'max-w-5xl', 'mx-auto px-6 py-4')}>
        <form onSubmit={handleSubmit} className="relative">
          <div
            className={clsx(
              'rounded-xl border transition-[background-color,border-color,box-shadow] duration-200',
              hasContent || isFocused
                ? 'border-amber-700/25 bg-white shadow-sm'
                : 'border-stone-200 bg-stone-50'
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
                'w-full rounded-t-xl bg-transparent px-4 pt-3 pb-1.5 text-stone-800',
                'resize-none outline-none placeholder:text-stone-400',
                'disabled:cursor-not-allowed disabled:opacity-60',
                'transition-colors duration-200',
                isOverflowing
                  ? 'scrollbar-thin scrollbar-thumb-stone-300 scrollbar-track-transparent overflow-y-auto'
                  : 'overflow-hidden'
              )}
              style={{ minHeight: '36px', maxHeight: `${MAX_HEIGHT}px` }}
            />

            <div className="flex items-center justify-between px-2.5 pb-2.5">
              <div className="flex items-center gap-2">
                {lineCount > 1 && (isFocused || query) && (
                  <span className="pointer-events-none text-xs text-stone-400">
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
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-500 text-white transition-colors hover:bg-red-600"
                    aria-label="Cancel"
                  >
                    <X className="h-4 w-4" strokeWidth={2} />
                  </motion.button>
                ) : (
                  <motion.button
                    key="send"
                    type="submit"
                    disabled={!hasContent}
                    {...buttonMotion}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-700 text-white transition-colors hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-40"
                    aria-label="Send"
                  >
                    <ArrowUp className="h-4 w-4" strokeWidth={2} />
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

import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import { Settings2, X, ArrowUp, RotateCcw } from 'lucide-react'
import type { LLMProvider } from '../../types/api'
import type { ChatOptions } from '../../hooks/useChat'
import { useSettingsStore } from '../../stores/settingsStore'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import Button from '../ui/Button'

interface ChatInputProps {
  onSend: (query: string, options: ChatOptions) => void
  isStreaming: boolean
  onCancel?: () => void
  variant?: 'bottom' | 'centered'
  defaultValue?: string
}

export default function ChatInput({ onSend, isStreaming, onCancel, variant = 'bottom', defaultValue }: ChatInputProps) {
  const [query, setQuery] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isFocused, setIsFocused] = useState(false)
  const [isOverflowing, setIsOverflowing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
    if (!query.trim() || isStreaming) return

    const options: ChatOptions = {
      provider,
      model,
      temperature,
      top_k,
      guardrail_threshold,
      max_retrieval_attempts,
      conversation_window,
    }

    onSend(query.trim(), options)
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

  return (
    <div className={isCentered ? '' : 'border-t border-stone-100 bg-white'}>
      <div className={`${isCentered ? 'max-w-2xl' : 'max-w-5xl'} mx-auto px-6 py-4`}>
        <form onSubmit={handleSubmit}>
          <AnimatedCollapse isOpen={showAdvanced}>
            <div className="mb-4">
              <div className="p-5 bg-stone-50 rounded-xl border border-stone-100">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="text-sm font-medium text-stone-700">Advanced Settings</h3>
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
                  <div>
                    <label className="block text-xs text-stone-500 mb-1.5">Provider</label>
                    <select
                      value={provider ?? ''}
                      onChange={(e) =>
                        setProvider((e.target.value || undefined) as LLMProvider | undefined)
                      }
                      className="w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150"
                    >
                      <option value="">Default</option>
                      <option value="openai">OpenAI</option>
                      <option value="zai">Z.AI</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs text-stone-500 mb-1.5">Model</label>
                    <input
                      type="text"
                      value={model ?? ''}
                      onChange={(e) => setModel(e.target.value || undefined)}
                      placeholder="Default"
                      className="w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150"
                    />
                  </div>

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
                      <span className="float-right font-mono text-stone-400">{top_k}</span>
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
                      onChange={(e) => setMaxRetrievalAttempts(parseInt(e.target.value))}
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
                      onChange={(e) => setConversationWindow(parseInt(e.target.value))}
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>
          </AnimatedCollapse>

          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder="Ask about research papers..."
                rows={1}
                disabled={isStreaming}
                className={`w-full px-4 py-2.5 pr-12 text-stone-800 bg-stone-50 border border-stone-200 rounded-xl resize-none placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 focus:bg-white disabled:opacity-60 disabled:cursor-not-allowed transition-[height,background-color,border-color,box-shadow] duration-150 ${isOverflowing ? 'overflow-y-auto scrollbar-thin scrollbar-thumb-stone-300 scrollbar-track-transparent' : 'overflow-hidden'} ${lineCount > 1 ? 'pb-6' : ''}`}
                style={{ minHeight: '44px', maxHeight: `${MAX_HEIGHT}px` }}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className={`absolute right-3 top-2.5 ${showAdvanced ? 'bg-stone-200 text-stone-700' : ''}`}
                aria-label="Advanced settings"
              >
                <Settings2 className="w-4 h-4" strokeWidth={1.5} />
              </Button>
              {lineCount > 1 && (isFocused || query) && (
                <span className="absolute right-3 bottom-2 text-xs text-stone-400 pointer-events-none transition-opacity duration-150">
                  {lineCount} lines
                </span>
              )}
            </div>

            {isStreaming ? (
              <button
                type="button"
                onClick={onCancel}
                className="flex-shrink-0 w-[50px] h-[50px] flex items-center justify-center bg-red-500 text-white hover:bg-red-600 rounded-xl transition-colors"
                aria-label="Cancel"
              >
                <X className="w-5 h-5" strokeWidth={2} />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!query.trim()}
                className="flex-shrink-0 w-[50px] h-[50px] flex items-center justify-center bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-colors"
                aria-label="Send"
              >
                <ArrowUp className="w-5 h-5" strokeWidth={2} />
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}

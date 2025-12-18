// Chat input with expandable advanced options

import { useState, type FormEvent, type KeyboardEvent } from 'react'
import type { LLMProvider } from '../../types/api'
import type { ChatOptions } from '../../hooks/useChat'
import { useSettingsStore } from '../../stores/settingsStore'

interface ChatInputProps {
  onSend: (query: string, options: ChatOptions) => void
  isStreaming: boolean
  onCancel?: () => void
}

export default function ChatInput({ onSend, isStreaming, onCancel }: ChatInputProps) {
  const [query, setQuery] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Use settings from store
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
    
    // Build options from current settings
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
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <form onSubmit={handleSubmit}>
        {/* Advanced options panel */}
        {showAdvanced && (
          <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200 transition-all duration-200">
            {/* Reset button */}
            <div className="flex justify-end mb-3">
              <button
                type="button"
                onClick={resetToDefaults}
                className="px-3 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-200 bg-gray-100 rounded-md transition-colors"
              >
                Reset to Defaults
              </button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* Provider */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Provider</label>
                <select
                  value={provider ?? ''}
                  onChange={(e) =>
                    setProvider((e.target.value || undefined) as LLMProvider | undefined)
                  }
                  className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-200"
                >
                  <option value="">Default</option>
                  <option value="openai">OpenAI</option>
                  <option value="zai">Z.AI</option>
                </select>
              </div>

              {/* Model */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Model</label>
                <input
                  type="text"
                  value={model ?? ''}
                  onChange={(e) => setModel(e.target.value || undefined)}
                  placeholder="Default model"
                  className="w-full px-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-200"
                />
              </div>

              {/* Temperature */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Temperature: {temperature.toFixed(1)}
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

              {/* Top K */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Top K: {top_k}
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

              {/* Guardrail Threshold */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Guardrail: {guardrail_threshold}%
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

              {/* Max Retrieval Attempts */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Max Retrieval: {max_retrieval_attempts}
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

              {/* Conversation Window */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Conversation Window: {conversation_window}
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
        )}

        {/* Input area */}
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              rows={1}
              disabled={isStreaming}
              className="w-full px-4 py-3 pr-10 border border-gray-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-gray-200 disabled:bg-gray-50 disabled:text-gray-500"
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`absolute right-3 bottom-3 p-1 rounded-md transition-colors ${
                showAdvanced ? 'text-gray-700 bg-gray-100' : 'text-gray-400 hover:text-gray-600'
              }`}
              title="Advanced options"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
            </button>
          </div>

          {isStreaming ? (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-3 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!query.trim()}
              className="px-4 py-3 bg-gray-900 text-white rounded-xl hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          )}
        </div>
      </form>
    </div>
  )
}

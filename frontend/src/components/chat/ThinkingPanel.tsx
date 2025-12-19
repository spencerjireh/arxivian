// Container for all thinking steps - collapsible panel like Claude UI

import { useState } from 'react'
import type { ThinkingStep } from '../../types/api'
import ThinkingStepItem from './ThinkingStepItem'

interface ThinkingPanelProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

export default function ThinkingPanel({ steps, isStreaming = false }: ThinkingPanelProps) {
  // Only track manual expansion state for after streaming completes
  // During streaming, panel is always expanded
  const [isManuallyExpanded, setIsManuallyExpanded] = useState(false)

  // Don't render if no steps
  if (steps.length === 0) {
    return null
  }

  // Count completed and total steps
  const completedCount = steps.filter((s) => s.status === 'complete').length
  const totalCount = steps.length

  // During streaming, always show expanded
  // After streaming, show collapsed with "View thinking" button
  if (isStreaming) {
    return (
      <div className="mb-3">
        {/* Streaming header */}
        <div className="flex items-center gap-2 mb-2">
          <svg
            className="w-4 h-4 text-gray-500 animate-pulse"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <span className="text-sm text-gray-600 font-medium">Thinking...</span>
        </div>

        {/* Steps list - always expanded during streaming */}
        <div className="space-y-2">
          {steps.map((step) => (
            <ThinkingStepItem key={step.id} step={step} isExpanded={true} />
          ))}
        </div>
      </div>
    )
  }

  // After streaming - collapsible panel
  return (
    <div className="mb-3">
      {/* Collapsed header - clickable to expand */}
      <button
        onClick={() => setIsManuallyExpanded(!isManuallyExpanded)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors w-full"
      >
        <svg
          className={`w-4 h-4 transition-transform ${isManuallyExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>

        {/* Thinking icon */}
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>

        <span>
          {isManuallyExpanded ? 'Hide thinking' : 'View thinking'}{' '}
          <span className="text-gray-400">
            ({completedCount}/{totalCount} steps)
          </span>
        </span>
      </button>

      {/* Expanded content */}
      {isManuallyExpanded && (
        <div className="mt-2 space-y-2 pl-6">
          {steps.map((step) => (
            <ThinkingStepItem key={step.id} step={step} isExpanded={false} />
          ))}
        </div>
      )}
    </div>
  )
}

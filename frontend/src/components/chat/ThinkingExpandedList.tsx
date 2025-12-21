// Post-streaming expandable list showing all completed steps with durations

import { useState } from 'react'
import { Check, X, ChevronDown, ChevronRight, Clock } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'
import { getStepDuration, formatDuration } from '../../stores/chatStore'

interface ThinkingExpandedListProps {
  steps: ThinkingStep[]
  totalDuration: number
}

export default function ThinkingExpandedList({ steps, totalDuration }: ThinkingExpandedListProps) {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null)

  // Sort steps by order
  const sortedSteps = [...steps].sort((a, b) => a.order - b.order)

  // Format detail value for display
  const formatDetailValue = (key: string, value: unknown): string => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (typeof value === 'number') {
      if (key.includes('score') || key.includes('threshold')) {
        return `${value}%`
      }
      return value.toString()
    }
    if (typeof value === 'string') {
      return value.length > 100 ? `${value.slice(0, 100)}...` : value
    }
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(', ') : '-'
    }
    return JSON.stringify(value)
  }

  const formatDetailKey = (key: string): string => {
    return key
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, (str) => str.toUpperCase())
      .trim()
  }

  return (
    <div className="space-y-1">
      {sortedSteps.map((step) => {
        const hasDetails = step.details && Object.keys(step.details).length > 0
        const isExpanded = expandedStepId === step.id
        const duration = getStepDuration(step)

        return (
          <div key={step.id} className="border-l-2 border-gray-200 pl-3">
            {/* Step row */}
            <div
              className={`
                flex items-center gap-2 py-1.5 text-sm
                ${hasDetails ? 'cursor-pointer hover:bg-gray-50 -ml-3 pl-3 rounded-r' : ''}
              `}
              onClick={() => hasDetails && setExpandedStepId(isExpanded ? null : step.id)}
            >
              {/* Status icon */}
              {step.status === 'complete' ? (
                <Check className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
              ) : (
                <X className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
              )}

              {/* Step label */}
              <span className="text-gray-600 font-medium min-w-[80px]">
                {STEP_LABELS[step.step]}
              </span>

              {/* Step message (truncated) */}
              <span className="text-gray-500 flex-1 truncate">{step.message}</span>

              {/* Duration */}
              <span className="text-xs text-gray-400 font-mono flex-shrink-0">
                {formatDuration(duration)}
              </span>

              {/* Expand indicator */}
              {hasDetails && (
                <div className="flex-shrink-0 text-gray-400">
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5" />
                  )}
                </div>
              )}
            </div>

            {/* Expanded details */}
            {hasDetails && isExpanded && step.details && (
              <div className="ml-5 pb-2 pt-1 text-xs animate-slide-down">
                <div className="bg-gray-50 rounded p-2 space-y-1">
                  {Object.entries(step.details).map(([key, value]) => (
                    <div key={key} className="flex">
                      <span className="text-gray-400 min-w-[100px]">{formatDetailKey(key)}</span>
                      <span className="text-gray-600 break-words">{formatDetailValue(key, value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* Total duration footer */}
      <div className="flex items-center gap-2 pt-2 mt-2 border-t border-gray-100 text-xs text-gray-400">
        <Clock className="w-3 h-3" />
        <span>Total: {formatDuration(totalDuration)}</span>
      </div>
    </div>
  )
}

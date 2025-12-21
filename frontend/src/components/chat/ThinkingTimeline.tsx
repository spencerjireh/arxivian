// Main container for thinking steps visualization
// Combines stepper, current step, and expanded list views

import { useState, useMemo } from 'react'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { formatDuration } from '../../stores/chatStore'
import ThinkingStepper from './ThinkingStepper'
import ThinkingCurrentStep from './ThinkingCurrentStep'
import ThinkingExpandedList from './ThinkingExpandedList'

interface ThinkingTimelineProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

export default function ThinkingTimeline({ steps, isStreaming = false }: ThinkingTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Find the currently running step (if any)
  const currentStep = useMemo(() => {
    return steps.find((s) => s.status === 'running')
  }, [steps])

  // Calculate total duration
  // For completed steps, use endTime. For streaming, we don't show duration in header anyway.
  const totalDuration = useMemo(() => {
    if (steps.length === 0) return 0
    const firstStart = Math.min(...steps.map((s) => s.startTime.getTime()))
    // Use the last step's endTime if available, otherwise use the last step's startTime
    // This avoids calling Date.now() during render which is impure
    const endTimes = steps
      .map((s) => s.endTime?.getTime())
      .filter((t): t is number => t !== undefined)
    const lastEnd = endTimes.length > 0
      ? Math.max(...endTimes)
      : Math.max(...steps.map((s) => s.startTime.getTime()))
    return lastEnd - firstStart
  }, [steps])

  // Don't render if no steps
  if (steps.length === 0) {
    return null
  }

  // During streaming: show stepper + current step details
  if (isStreaming) {
    return (
      <div className="mb-3 space-y-3">
        {/* Header */}
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-gray-500 step-pulse" />
          <span className="text-sm text-gray-600 font-medium">Thinking...</span>
        </div>

        {/* Stepper showing all steps that have occurred */}
        <ThinkingStepper steps={steps} />

        {/* Current step details (if there's a running step) */}
        {currentStep && <ThinkingCurrentStep step={currentStep} />}
      </div>
    )
  }

  // After streaming: collapsible summary
  return (
    <div className="mb-3">
      {/* Collapsed header - clickable to expand */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors w-full group"
      >
        {/* Expand/collapse indicator */}
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 transition-transform" />
        ) : (
          <ChevronRight className="w-4 h-4 transition-transform" />
        )}

        {/* Brain icon */}
        <Brain className="w-4 h-4" />

        {/* Summary text */}
        <span>
          {isExpanded ? 'Hide' : 'View'} thinking process
          <span className="text-gray-400 ml-1">
            ({steps.length} step{steps.length !== 1 ? 's' : ''}, {formatDuration(totalDuration)})
          </span>
        </span>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="mt-2 pl-6 animate-slide-down">
          <ThinkingExpandedList steps={steps} totalDuration={totalDuration} />
        </div>
      )}
    </div>
  )
}

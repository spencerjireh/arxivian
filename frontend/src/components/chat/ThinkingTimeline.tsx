// Main container for thinking steps visualization

import { useState, useMemo } from 'react'
import { Lightbulb, ChevronDown, ChevronRight } from 'lucide-react'
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
  const totalDuration = useMemo(() => {
    if (steps.length === 0) return 0
    const firstStart = Math.min(...steps.map((s) => s.startTime.getTime()))
    const endTimes = steps
      .map((s) => s.endTime?.getTime())
      .filter((t): t is number => t !== undefined)
    const lastEnd = endTimes.length > 0
      ? Math.max(...endTimes)
      : Math.max(...steps.map((s) => s.startTime.getTime()))
    return lastEnd - firstStart
  }, [steps])

  if (steps.length === 0) {
    return null
  }

  // During streaming: show stepper + current step details
  if (isStreaming) {
    return (
      <div className="p-4 bg-amber-50/50 border border-amber-100 rounded-xl space-y-4">
        {/* Header */}
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-600 step-pulse" strokeWidth={1.5} />
          <span className="text-sm font-medium text-amber-800">Processing...</span>
        </div>

        {/* Stepper showing all steps that have occurred */}
        <ThinkingStepper steps={steps} />

        {/* Current step details */}
        {currentStep && <ThinkingCurrentStep step={currentStep} />}
      </div>
    )
  }

  // After streaming: collapsible summary
  return (
    <div className="rounded-xl border border-stone-100 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-stone-50 transition-colors duration-150"
      >
        <div className="flex items-center gap-2.5">
          <Lightbulb className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
          <span className="text-sm text-stone-600">
            {isExpanded ? 'Hide' : 'View'} reasoning
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-stone-400 font-mono">
            {steps.length} step{steps.length !== 1 ? 's' : ''} / {formatDuration(totalDuration)}
          </span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
          ) : (
            <ChevronRight className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 pt-1 animate-slide-down">
          <ThinkingExpandedList steps={steps} totalDuration={totalDuration} />
        </div>
      )}
    </div>
  )
}

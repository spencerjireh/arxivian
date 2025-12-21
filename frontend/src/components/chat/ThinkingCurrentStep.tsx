// Shows details of the currently running step with live elapsed time

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'
import { formatDuration } from '../../stores/chatStore'

interface ThinkingCurrentStepProps {
  step: ThinkingStep
}

export default function ThinkingCurrentStep({ step }: ThinkingCurrentStepProps) {
  const [elapsed, setElapsed] = useState(0)

  // Update elapsed time every 100ms for running steps
  useEffect(() => {
    if (step.status !== 'running') {
      return
    }

    const interval = setInterval(() => {
      setElapsed(Date.now() - step.startTime.getTime())
    }, 100)

    return () => clearInterval(interval)
  }, [step.status, step.startTime])

  // Format details for display
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
      return value.length > 80 ? `${value.slice(0, 80)}...` : value
    }
    if (Array.isArray(value)) {
      return value.length > 0 ? value.slice(0, 3).join(', ') + (value.length > 3 ? '...' : '') : '-'
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

  const hasDetails = step.details && Object.keys(step.details).length > 0

  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
      {/* Header with step name and elapsed time */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />
          <span className="text-sm font-medium text-gray-700">
            {STEP_LABELS[step.step]}
          </span>
        </div>
        <span className="text-xs text-gray-400 font-mono">
          {formatDuration(elapsed)}
        </span>
      </div>

      {/* Status message */}
      <p className="text-sm text-gray-600 mb-2">{step.message}</p>

      {/* Key details (if any) */}
      {hasDetails && step.details && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {Object.entries(step.details)
            .slice(0, 4) // Show max 4 details
            .map(([key, value]) => (
              <div key={key} className="flex items-center gap-1">
                <span className="text-gray-400">{formatDetailKey(key)}:</span>
                <span className="text-gray-600">{formatDetailValue(key, value)}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

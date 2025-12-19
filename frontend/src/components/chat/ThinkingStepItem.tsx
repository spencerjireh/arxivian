// Individual thinking step component with icon and expandable details

import { useState } from 'react'
import {
  ShieldCheck,
  ClipboardCheck,
  Settings,
  ClipboardList,
  Pencil,
  AlertTriangle,
  Info,
  Loader2,
  Check,
  X,
  ChevronDown,
} from 'lucide-react'
import type { ThinkingStep, ThinkingStepType } from '../../types/api'

interface ThinkingStepItemProps {
  step: ThinkingStep
  isExpanded?: boolean
}

// Get icon and color for each step type
function getStepConfig(stepType: ThinkingStepType): {
  icon: React.ReactNode
  label: string
  bgColor: string
  textColor: string
} {
  switch (stepType) {
    case 'guardrail':
      return {
        icon: <ShieldCheck className="w-4 h-4" />,
        label: 'Guardrail',
        bgColor: 'bg-blue-50',
        textColor: 'text-blue-700',
      }
    case 'routing':
      return {
        icon: <ClipboardCheck className="w-4 h-4" />,
        label: 'Routing',
        bgColor: 'bg-purple-50',
        textColor: 'text-purple-700',
      }
    case 'executing':
      return {
        icon: <Settings className="w-4 h-4" />,
        label: 'Tool',
        bgColor: 'bg-amber-50',
        textColor: 'text-amber-700',
      }
    case 'grading':
      return {
        icon: <ClipboardList className="w-4 h-4" />,
        label: 'Grading',
        bgColor: 'bg-green-50',
        textColor: 'text-green-700',
      }
    case 'generation':
      return {
        icon: <Pencil className="w-4 h-4" />,
        label: 'Generating',
        bgColor: 'bg-indigo-50',
        textColor: 'text-indigo-700',
      }
    case 'out_of_scope':
      return {
        icon: <AlertTriangle className="w-4 h-4" />,
        label: 'Out of Scope',
        bgColor: 'bg-orange-50',
        textColor: 'text-orange-700',
      }
    default:
      return {
        icon: <Info className="w-4 h-4" />,
        label: 'Processing',
        bgColor: 'bg-gray-50',
        textColor: 'text-gray-700',
      }
  }
}

// Format detail value for display
function formatDetailValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return '-'

  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    // Format percentages
    if (key.includes('score') || key.includes('threshold')) {
      return `${value}%`
    }
    return value.toString()
  }
  if (typeof value === 'string') {
    // Truncate long strings
    return value.length > 100 ? `${value.slice(0, 100)}...` : value
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : '-'
  }
  return JSON.stringify(value)
}

// Format detail key for display
function formatDetailKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim()
}

export default function ThinkingStepItem({ step, isExpanded = false }: ThinkingStepItemProps) {
  const [showDetails, setShowDetails] = useState(isExpanded)
  const config = getStepConfig(step.step)
  const hasDetails = step.details && Object.keys(step.details).length > 0

  return (
    <div className={`rounded-lg border ${config.bgColor} border-opacity-50 overflow-hidden`}>
      {/* Step header */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${hasDetails ? 'cursor-pointer hover:bg-opacity-70' : ''}`}
        onClick={() => hasDetails && setShowDetails(!showDetails)}
      >
        {/* Status indicator */}
        {step.status === 'running' ? (
          <Loader2 className={`w-4 h-4 animate-spin ${config.textColor}`} />
        ) : step.status === 'complete' ? (
          <Check className="w-4 h-4 text-green-600" />
        ) : (
          <X className="w-4 h-4 text-red-600" />
        )}

        {/* Step icon */}
        <span className={config.textColor}>{config.icon}</span>

        {/* Step message */}
        <span className={`flex-1 text-sm ${config.textColor}`}>{step.message}</span>

        {/* Expand indicator */}
        {hasDetails && (
          <ChevronDown
            className={`w-4 h-4 transition-transform ${config.textColor} ${showDetails ? 'rotate-180' : ''}`}
          />
        )}
      </div>

      {/* Details panel */}
      {hasDetails && showDetails && step.details && (
        <div className="px-3 pb-2 pt-1 border-t border-gray-200 border-opacity-50">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {Object.entries(step.details).map(([key, value]) => (
              <div key={key} className="flex flex-col">
                <span className="text-gray-500">{formatDetailKey(key)}</span>
                <span className={`${config.textColor} break-words`}>
                  {formatDetailValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

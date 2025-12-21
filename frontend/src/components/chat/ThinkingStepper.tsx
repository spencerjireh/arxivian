// Horizontal step indicator showing workflow progress
// Only shows steps that have actually occurred (not all possible steps)

import { Check, Loader2 } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'

interface ThinkingStepperProps {
  steps: ThinkingStep[]
}

export default function ThinkingStepper({ steps }: ThinkingStepperProps) {
  if (steps.length === 0) return null

  // Sort steps by order for consistent display
  const sortedSteps = [...steps].sort((a, b) => a.order - b.order)

  return (
    <div className="flex flex-col gap-2">
      {/* Desktop: horizontal stepper */}
      <div className="hidden sm:flex items-center gap-1">
        {sortedSteps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            {/* Step indicator */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium
                  transition-all duration-200
                  ${
                    step.status === 'running'
                      ? 'bg-gray-200 text-gray-600 step-pulse'
                      : step.status === 'complete'
                        ? 'bg-gray-700 text-white'
                        : 'bg-red-100 text-red-600'
                  }
                `}
              >
                {step.status === 'running' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : step.status === 'complete' ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <span className="text-xs">!</span>
                )}
              </div>
              <span
                className={`
                  text-xs mt-1 whitespace-nowrap
                  ${step.status === 'running' ? 'text-gray-700 font-medium' : 'text-gray-500'}
                `}
              >
                {STEP_LABELS[step.step]}
              </span>
            </div>

            {/* Connector line (not after last step) */}
            {index < sortedSteps.length - 1 && (
              <div
                className={`
                  w-8 h-0.5 mx-1 transition-colors duration-200
                  ${step.status === 'complete' ? 'bg-gray-400' : 'bg-gray-200'}
                `}
              />
            )}
          </div>
        ))}
      </div>

      {/* Mobile: vertical stepper */}
      <div className="flex sm:hidden flex-col gap-1">
        {sortedSteps.map((step, index) => (
          <div key={step.id} className="flex items-start gap-2">
            {/* Vertical line and indicator */}
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-5 h-5 rounded-full flex items-center justify-center text-xs
                  transition-all duration-200
                  ${
                    step.status === 'running'
                      ? 'bg-gray-200 text-gray-600 step-pulse'
                      : step.status === 'complete'
                        ? 'bg-gray-700 text-white'
                        : 'bg-red-100 text-red-600'
                  }
                `}
              >
                {step.status === 'running' ? (
                  <Loader2 className="w-2.5 h-2.5 animate-spin" />
                ) : step.status === 'complete' ? (
                  <Check className="w-2.5 h-2.5" />
                ) : (
                  <span className="text-xs">!</span>
                )}
              </div>
              {/* Vertical connector */}
              {index < sortedSteps.length - 1 && (
                <div
                  className={`
                    w-0.5 h-4 transition-colors duration-200
                    ${step.status === 'complete' ? 'bg-gray-400' : 'bg-gray-200'}
                  `}
                />
              )}
            </div>

            {/* Step label */}
            <span
              className={`
                text-sm leading-5
                ${step.status === 'running' ? 'text-gray-700 font-medium' : 'text-gray-500'}
              `}
            >
              {STEP_LABELS[step.step]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

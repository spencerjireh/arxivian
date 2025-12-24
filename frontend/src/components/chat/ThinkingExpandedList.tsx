import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Check, AlertCircle, ChevronRight, Clock } from 'lucide-react'
import clsx from 'clsx'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'
import { getStepDuration, formatDuration } from '../../utils/duration'
import { formatDetailKey, formatDetailValue } from '../../utils/formatting'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { transitions } from '../../lib/animations'
import ThinkingStepper from './ThinkingStepper'

interface ThinkingExpandedListProps {
  steps: ThinkingStep[]
  totalDuration: number
}

export default function ThinkingExpandedList({ steps, totalDuration }: ThinkingExpandedListProps) {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null)
  const shouldReduceMotion = useReducedMotion()

  const sortedSteps = [...steps].sort((a, b) => a.order - b.order)

  return (
    <div className="space-y-4">
      {/* Static stepper visualization */}
      <div className="pb-3 border-b border-stone-100">
        <ThinkingStepper steps={steps} isStatic />
      </div>

      {/* Step details list */}
      <div className="space-y-1">
        {sortedSteps.map((step) => {
        const hasDetails = step.details && Object.keys(step.details).length > 0
        const isExpanded = expandedStepId === step.id
        const duration = getStepDuration(step)

        return (
          <div key={step.id}>
            <div
              className={clsx(
                'flex items-center gap-3 py-2.5 px-3 rounded-lg text-sm',
                'transition-colors duration-150',
                hasDetails && 'cursor-pointer hover:bg-stone-50'
              )}
              onClick={() => hasDetails && setExpandedStepId(isExpanded ? null : step.id)}
            >
              <div
                className={clsx(
                  'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0',
                  step.status === 'complete' ? 'bg-stone-100' : 'bg-red-100'
                )}
              >
                {step.status === 'complete' ? (
                  <Check className="w-3 h-3 text-stone-600" strokeWidth={2} />
                ) : (
                  <AlertCircle className="w-3 h-3 text-red-500" strokeWidth={1.5} />
                )}
              </div>

              <span className="text-stone-700 font-medium min-w-[80px]">
                {STEP_LABELS[step.step]}
              </span>

              <span className="text-stone-500 flex-1 truncate">{step.message}</span>

              <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
                {formatDuration(duration)}
              </span>

              {hasDetails && (
                <motion.div
                  className="flex-shrink-0 text-stone-300"
                  animate={{ rotate: isExpanded ? 90 : 0 }}
                  transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
                >
                  <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
                </motion.div>
              )}
            </div>

            {hasDetails && (
              <AnimatedCollapse isOpen={isExpanded}>
                <div className="ml-11 mr-3 mb-2">
                  <div className="bg-stone-50 rounded-lg p-3 space-y-1.5">
                    {step.details && Object.entries(step.details).map(([key, value]) => (
                      <div key={key} className="flex text-xs">
                        <span className="text-stone-400 min-w-[100px] flex-shrink-0">
                          {formatDetailKey(key)}
                        </span>
                        <span className="text-stone-600 break-words font-mono">
                          {formatDetailValue(key, value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </AnimatedCollapse>
            )}
          </div>
        )
      })}

        <div className="flex items-center gap-2 pt-3 mt-2 border-t border-stone-100 text-xs text-stone-400 px-3">
          <Clock className="w-3.5 h-3.5" strokeWidth={1.5} />
          <span>Total processing time: {formatDuration(totalDuration)}</span>
        </div>
      </div>
    </div>
  )
}

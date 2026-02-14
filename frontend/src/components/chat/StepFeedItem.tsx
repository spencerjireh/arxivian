import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'
import type { ThinkingStep } from '../../types/api'
import { STEP_CONFIG } from '../../lib/thinking/constants'
import { getStepDuration, formatDuration } from '../../utils/duration'
import { formatDetailKey, formatDetailValue } from '../../utils/formatting'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { staggerItem, transitions } from '../../lib/animations'

interface StepFeedItemProps {
  step: ThinkingStep
  isStreaming: boolean
}

export default function StepFeedItem({ step, isStreaming }: StepFeedItemProps) {
  const [elapsed, setElapsed] = useState(0)
  const [isExpanded, setIsExpanded] = useState(false)

  const config = STEP_CONFIG[step.step]
  const StepIcon = config.icon
  const hasDetails = !isStreaming && step.details && Object.keys(step.details).length > 0

  useEffect(() => {
    if (step.status !== 'running') return

    const interval = setInterval(() => {
      setElapsed(Date.now() - step.startTime.getTime())
    }, 100)

    return () => clearInterval(interval)
  }, [step.status, step.startTime])

  const duration = step.status === 'running' ? elapsed : getStepDuration(step)

  return (
    <motion.div
      variants={staggerItem}
      transition={transitions.base}
      className="py-1"
    >
      <div
        className={clsx(
          'flex items-center gap-3 py-1.5 px-2 -mx-2 rounded-md',
          'transition-colors duration-150',
          hasDetails && 'cursor-pointer hover:bg-stone-50'
        )}
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
      >
        {step.status === 'running' ? (
          <Loader2
            className="w-4 h-4 text-amber-600 animate-spin flex-shrink-0"
            strokeWidth={1.5}
          />
        ) : (
          <StepIcon
            className={clsx(
              'w-4 h-4 flex-shrink-0',
              step.status === 'complete' && 'text-stone-400',
              step.status === 'error' && 'text-red-400'
            )}
            strokeWidth={1.5}
          />
        )}

        <span
          className={clsx(
            'flex-1 text-sm',
            step.status === 'running' && 'text-amber-700 font-medium',
            step.status === 'complete' && 'text-stone-600',
            step.status === 'error' && 'text-red-500 line-through'
          )}
        >
          {step.message}
        </span>

        <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
          {formatDuration(duration)}
        </span>
      </div>

      {hasDetails && (
        <AnimatedCollapse isOpen={isExpanded}>
          <div className="ml-7 border-l border-stone-200/50 pl-3 py-2 mb-1">
            {step.details && Object.entries(step.details).map(([key, value]) => (
              <div key={key} className="flex text-xs leading-relaxed py-0.5">
                <span className="text-stone-400 min-w-[90px] flex-shrink-0">
                  {formatDetailKey(key)}
                </span>
                <span className="text-stone-500 break-words font-mono">
                  {formatDetailValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </AnimatedCollapse>
      )}
    </motion.div>
  )
}

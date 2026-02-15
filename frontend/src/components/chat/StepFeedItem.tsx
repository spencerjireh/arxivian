import { useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import type { ThinkingStep } from '../../types/api'
import { STEP_CONFIG } from '../../lib/thinking/constants'
import { getStepDuration, formatDuration } from '../../utils/duration'
import { formatDetailKey, formatDetailValue } from '../../utils/formatting'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { staggerItem, transitions } from '../../lib/animations'

const LABEL_MIN_WIDTH_PX = 100
const GAP_PX = 12 // gap-3
const DETAILS_INDENT_PX = LABEL_MIN_WIDTH_PX + GAP_PX

interface StepFeedItemProps {
  step: ThinkingStep
  isStreaming: boolean
}

export default function StepFeedItem({ step, isStreaming }: StepFeedItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const config = STEP_CONFIG[step.step]
  const hasDetails = !isStreaming && step.details && Object.keys(step.details).length > 0

  const label = step.toolName ?? config.label

  const duration = step.status === 'complete' ? getStepDuration(step) : null

  return (
    <motion.div
      variants={staggerItem}
      transition={transitions.base}
      className="py-0.5"
    >
      <div
        className={clsx(
          'flex items-baseline gap-3 py-1 px-1 -mx-1 rounded',
          'transition-colors duration-150',
          hasDetails && 'cursor-pointer hover:bg-stone-50/60'
        )}
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
      >
        <span
          className="font-display text-xs text-stone-400 flex-shrink-0 italic"
          style={{ minWidth: LABEL_MIN_WIDTH_PX }}
        >
          {label}
        </span>

        <span
          className={clsx(
            'flex-1 text-xs',
            step.status === 'error' ? 'text-red-500 line-through' : 'text-stone-500'
          )}
        >
          {step.message}
        </span>

        {duration !== null && (
          <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
            {formatDuration(duration)}
          </span>
        )}
      </div>

      {hasDetails && (
        <AnimatedCollapse isOpen={isExpanded}>
          <div
            className="border-l border-stone-200/50 pl-3 py-2 mb-1"
            style={{ marginLeft: DETAILS_INDENT_PX }}
          >
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

import { useState, useEffect } from 'react'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { Loader2, X } from 'lucide-react'
import clsx from 'clsx'
import type { ActivityStep } from '../../types/api'
import { getStepDuration, formatDuration } from '../../utils/duration'
import { staggerItem, transitions } from '../../lib/animations'
import { STEP_ICONS, STEP_ICON_COLORS } from '../../lib/thinking/constants'

interface ActivityListProps {
  steps: ActivityStep[]
}

function ElapsedTimer({ startTime }: { startTime: Date }) {
  const [elapsed, setElapsed] = useState(() => Date.now() - startTime.getTime())

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - startTime.getTime())
    }, 100)
    return () => clearInterval(interval)
  }, [startTime])

  return (
    <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
      {formatDuration(elapsed)}
    </span>
  )
}

function StatusIcon({ step }: { step: ActivityStep }) {
  if (step.status === 'error') {
    return <X className="w-3.5 h-3.5 text-red-500" strokeWidth={2} />
  }
  if (step.status === 'running') {
    const Icon = STEP_ICONS[step.kind]
    if (Icon) {
      return <Icon className={clsx('w-3.5 h-3.5', STEP_ICON_COLORS[step.kind])} strokeWidth={1.5} />
    }
    return <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin" strokeWidth={1.5} />
  }
  // complete
  const Icon = STEP_ICONS[step.kind]
  if (Icon) {
    return <Icon className="w-3.5 h-3.5 text-stone-400" strokeWidth={1.5} />
  }
  return null
}

export default function ActivityList({ steps }: ActivityListProps) {
  const shouldReduceMotion = useReducedMotion()

  if (steps.length === 0) return null

  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false}>
        {steps.map((step) => {
          const duration = getStepDuration(step)

          return (
            <motion.div
              key={step.id}
              variants={shouldReduceMotion ? {} : staggerItem}
              initial="initial"
              animate="animate"
              transition={transitions.fast}
              className="flex items-center gap-2.5 py-1.5 px-2 rounded-lg text-sm"
            >
              <div
                className={clsx(
                  'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0',
                  step.status === 'running' && 'bg-amber-50',
                  step.status === 'complete' && 'bg-stone-100',
                  step.status === 'error' && 'bg-red-50'
                )}
              >
                <StatusIcon step={step} />
              </div>

              <span className="text-stone-600 flex-1 truncate font-display italic font-normal">
                {step.message}
              </span>

              {step.status === 'running' ? (
                <ElapsedTimer startTime={step.startTime} />
              ) : (
                <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
                  {formatDuration(duration)}
                </span>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

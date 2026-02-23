import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { X } from 'lucide-react'
import clsx from 'clsx'
import type { ActivityStep } from '../../types/api'
import { staggerItem, completionPopVariants, transitions } from '../../lib/animations'
import { STEP_ICONS, STEP_ICON_COLORS, STEP_ANIMATION_VARIANTS } from '../../lib/thinking/constants'

interface ActivityListProps {
  steps: ActivityStep[]
  isStreaming?: boolean
}

function StatusIcon({ step, reduceMotion, isStreaming }: { step: ActivityStep; reduceMotion: boolean | null; isStreaming: boolean }) {
  const Icon = STEP_ICONS[step.kind]

  if (step.status === 'error') {
    return <X className="w-3.5 h-3.5 text-red-500" strokeWidth={2} />
  }

  if (!Icon) return null

  if (step.status === 'running') {
    const variants = STEP_ANIMATION_VARIANTS[step.kind]
    return (
      <motion.div
        variants={reduceMotion ? undefined : variants}
        animate="animate"
      >
        <Icon className={clsx('w-3.5 h-3.5', STEP_ICON_COLORS[step.kind])} strokeWidth={1.5} />
      </motion.div>
    )
  }

  // complete -- only pop when transitioning live, not on historical loads
  if (isStreaming) {
    return (
      <motion.div
        variants={reduceMotion ? undefined : completionPopVariants}
        initial="initial"
        animate="animate"
      >
        <Icon className="w-3.5 h-3.5 text-stone-400" strokeWidth={1.5} />
      </motion.div>
    )
  }

  return <Icon className="w-3.5 h-3.5 text-stone-400" strokeWidth={1.5} />
}

export default function ActivityList({ steps, isStreaming = false }: ActivityListProps) {
  const shouldReduceMotion = useReducedMotion()

  if (steps.length === 0) return null

  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false}>
        {steps.map((step) => {
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
                <StatusIcon step={step} reduceMotion={shouldReduceMotion} isStreaming={isStreaming} />
              </div>

              <span className="text-stone-600 flex-1 truncate font-display italic font-normal">
                {step.message}
              </span>

              {/* Per-step timing removed -- restore from git history when needed */}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

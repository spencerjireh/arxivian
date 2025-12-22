import { useState, useMemo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Lightbulb, ChevronRight } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { formatDuration } from '../../stores/chatStore'
import ThinkingStepper from './ThinkingStepper'
import ThinkingCurrentStep from './ThinkingCurrentStep'
import ThinkingExpandedList from './ThinkingExpandedList'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { pulseVariants, fadeInUp, transitions } from '../../lib/animations'

interface ThinkingTimelineProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

export default function ThinkingTimeline({ steps, isStreaming = false }: ThinkingTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const shouldReduceMotion = useReducedMotion()

  const currentStep = useMemo(() => {
    return steps.find((s) => s.status === 'running')
  }, [steps])

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

  if (isStreaming) {
    return (
      <motion.div
        className="p-4 bg-amber-50/50 border border-amber-100 rounded-xl space-y-4"
        variants={fadeInUp}
        initial="initial"
        animate="animate"
        transition={transitions.fast}
      >
        <div className="flex items-center gap-2">
          <motion.div
            variants={shouldReduceMotion ? {} : pulseVariants}
            animate="animate"
          >
            <Lightbulb className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
          </motion.div>
          <span className="text-sm font-medium text-amber-800">Processing...</span>
        </div>

        <ThinkingStepper steps={steps} />

        {currentStep && <ThinkingCurrentStep step={currentStep} />}
      </motion.div>
    )
  }

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
          <motion.div
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={transitions.fast}
          >
            <ChevronRight className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
          </motion.div>
        </div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="px-4 pb-4 pt-1">
          <ThinkingExpandedList steps={steps} totalDuration={totalDuration} />
        </div>
      </AnimatedCollapse>
    </div>
  )
}

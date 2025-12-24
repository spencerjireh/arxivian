import { useState, useMemo, useRef, useEffect } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ChevronRight } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { calculateTotalDuration, formatDuration } from '../../utils/duration'
import ThinkingStepper from './ThinkingStepper'
import ThinkingCurrentStep from './ThinkingCurrentStep'
import ThinkingExpandedList from './ThinkingExpandedList'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { pulseVariants, fadeIn, transitions } from '../../lib/animations'

interface ThinkingTimelineProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

export default function ThinkingTimeline({ steps, isStreaming = false }: ThinkingTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showExpandedAfterStream, setShowExpandedAfterStream] = useState(false)
  const prevIsStreaming = useRef(isStreaming)
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (prevIsStreaming.current && !isStreaming) {
      // Show expanded view for 1.5s after streaming ends, then collapse
      queueMicrotask(() => setShowExpandedAfterStream(true))

      const collapseTimer = setTimeout(
        () => {
          setShowExpandedAfterStream(false)
        },
        shouldReduceMotion ? 0 : 1500
      )

      return () => clearTimeout(collapseTimer)
    }
    prevIsStreaming.current = isStreaming
  }, [isStreaming, shouldReduceMotion])

  const currentStep = useMemo(() => {
    return steps.find((s) => s.status === 'running')
  }, [steps])

  const totalDuration = useMemo(() => calculateTotalDuration(steps), [steps])

  if (steps.length === 0) {
    return null
  }

  return (
    <AnimatePresence mode="wait">
      {isStreaming ? (
        <motion.div
          key="streaming"
          className="p-4 bg-amber-50/50 border border-amber-100 rounded-xl space-y-4"
          variants={fadeIn}
          initial="initial"
          animate="animate"
          exit={{ opacity: 0 }}
          transition={transitions.fast}
          style={{ contain: 'layout' }}
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
      ) : (
        <motion.div
          key="accordion"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={transitions.fast}
          className="rounded-xl border border-stone-100 overflow-hidden"
        >
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

          <AnimatedCollapse isOpen={isExpanded || showExpandedAfterStream}>
            <div className="px-4 pb-4 pt-1">
              <ThinkingExpandedList steps={steps} totalDuration={totalDuration} />
            </div>
          </AnimatedCollapse>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

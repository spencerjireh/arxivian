import { useState, useMemo } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { ChevronRight, Eye, EyeOff } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_CONFIG } from '../../lib/thinking/constants'
import { calculateTotalDuration, formatDuration } from '../../utils/duration'
import { useSettingsStore } from '../../stores/settingsStore'
import StepFeedItem from './StepFeedItem'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { fadeIn, staggerContainer, transitions } from '../../lib/animations'

interface StepActivityFeedProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
}

export default function StepActivityFeed({
  steps,
  isStreaming = false,
}: StepActivityFeedProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showHiddenSteps, setShowHiddenSteps] = useState(false)
  const shouldReduceMotion = useReducedMotion()
  const showAgentInternals = useSettingsStore((s) => s.showAgentInternals)

  const visibleSteps = useMemo(() => {
    const sorted = [...steps].sort((a, b) => a.order - b.order)
    if (showAgentInternals || showHiddenSteps) return sorted
    return sorted.filter((s) => STEP_CONFIG[s.step].visible)
  }, [steps, showAgentInternals, showHiddenSteps])

  const hasHiddenSteps = useMemo(() => {
    if (showAgentInternals) return false
    return steps.some((s) => !STEP_CONFIG[s.step].visible)
  }, [steps, showAgentInternals])

  const totalDuration = useMemo(() => calculateTotalDuration(steps), [steps])
  const completedSteps = useMemo(
    () => isStreaming ? visibleSteps.filter((s) => s.status !== 'running') : [],
    [visibleSteps, isStreaming]
  )

  if (steps.length === 0) return null

  const stepList = (
    <motion.div
      variants={shouldReduceMotion ? {} : staggerContainer}
      initial="initial"
      animate="animate"
    >
      {visibleSteps.map((step) => (
        <StepFeedItem key={step.id} step={step} isStreaming={isStreaming} />
      ))}
    </motion.div>
  )

  return (
    <AnimatePresence mode="wait">
      {isStreaming ? (
        <motion.div
          key="streaming"
          variants={fadeIn}
          initial="initial"
          animate="animate"
          exit={{ opacity: 0 }}
          transition={transitions.fast}
          style={{ contain: 'layout' }}
        >
          <p className="font-display text-sm italic text-shimmer mb-2">
            Reasoning...
          </p>

          {completedSteps.length > 0 && (
            <motion.div
              variants={shouldReduceMotion ? {} : staggerContainer}
              initial="initial"
              animate="animate"
            >
              {completedSteps.map((step) => (
                <StepFeedItem key={step.id} step={step} isStreaming={isStreaming} />
              ))}
            </motion.div>
          )}
        </motion.div>
      ) : (
        <motion.div
          key="collapsed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={transitions.fast}
        >
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="group flex items-center gap-1.5 py-1 hover:opacity-70 transition-opacity duration-150"
            >
              <motion.div
                animate={{ rotate: isExpanded ? 90 : 0 }}
                transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
              >
                <ChevronRight className="w-3.5 h-3.5 text-stone-300" strokeWidth={1.5} />
              </motion.div>
              <span className="font-display text-sm text-stone-400 italic tracking-wide">
                Reasoned for {formatDuration(totalDuration)}
              </span>
            </button>

            {isExpanded && hasHiddenSteps && (
              <button
                onClick={() => setShowHiddenSteps(!showHiddenSteps)}
                className="flex items-center gap-1 py-1 hover:opacity-70 transition-opacity duration-150"
              >
                {showHiddenSteps
                  ? <EyeOff className="w-3.5 h-3.5 text-stone-300" strokeWidth={1.5} />
                  : <Eye className="w-3.5 h-3.5 text-stone-300" strokeWidth={1.5} />
                }
                <span className="font-display text-sm text-stone-400 italic tracking-wide">
                  internals
                </span>
              </button>
            )}
          </div>

          <AnimatedCollapse isOpen={isExpanded}>
            <div className="mt-1 mb-1">
              {stepList}
            </div>
          </AnimatedCollapse>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

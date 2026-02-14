import { useState, useMemo, useRef, useEffect } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
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
  const [showExpandedAfterStream, setShowExpandedAfterStream] = useState(false)
  const [showHiddenSteps, setShowHiddenSteps] = useState(false)
  const prevIsStreaming = useRef(isStreaming)
  const shouldReduceMotion = useReducedMotion()
  const showAgentInternals = useSettingsStore((s) => s.showAgentInternals)

  useEffect(() => {
    if (prevIsStreaming.current && !isStreaming) {
      queueMicrotask(() => setShowExpandedAfterStream(true))

      const collapseTimer = setTimeout(
        () => { setShowExpandedAfterStream(false) },
        shouldReduceMotion ? 0 : 1500
      )

      return () => clearTimeout(collapseTimer)
    }
    prevIsStreaming.current = isStreaming
  }, [isStreaming, shouldReduceMotion])

  const { visibleSteps, hiddenSteps, allSorted } = useMemo(() => {
    const sorted = [...steps].sort((a, b) => a.order - b.order)
    if (showAgentInternals) {
      return { visibleSteps: sorted, hiddenSteps: [] as ThinkingStep[], allSorted: sorted }
    }
    return {
      visibleSteps: sorted.filter((s) => STEP_CONFIG[s.step].visible),
      hiddenSteps: sorted.filter((s) => !STEP_CONFIG[s.step].visible),
      allSorted: sorted,
    }
  }, [steps, showAgentInternals])

  const totalDuration = useMemo(() => calculateTotalDuration(steps), [steps])

  if (steps.length === 0) return null

  const displaySteps = showHiddenSteps ? allSorted : visibleSteps

  const hiddenToggle = !showAgentInternals && hiddenSteps.length > 0 && !showHiddenSteps && (
    <button
      onClick={(e) => {
        e.stopPropagation()
        setShowHiddenSteps(true)
      }}
      className="mt-1 text-xs text-stone-400 hover:text-stone-600 transition-colors duration-150"
    >
      + {hiddenSteps.length} internal step{hiddenSteps.length !== 1 ? 's' : ''}
    </button>
  )

  const stepList = (
    <motion.div
      variants={shouldReduceMotion ? {} : staggerContainer}
      initial="initial"
      animate="animate"
    >
      {displaySteps.map((step) => (
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
          {stepList}
          {hiddenToggle}
        </motion.div>
      ) : (
        <motion.div
          key="collapsed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={transitions.fast}
        >
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
              {steps.length} step{steps.length !== 1 ? 's' : ''}
              <span className="mx-1.5 text-stone-300">&middot;</span>
              {formatDuration(totalDuration)}
            </span>
          </button>

          <AnimatedCollapse isOpen={isExpanded || showExpandedAfterStream}>
            <div className="mt-1 mb-1">
              {stepList}
              {hiddenToggle}
            </div>
          </AnimatedCollapse>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

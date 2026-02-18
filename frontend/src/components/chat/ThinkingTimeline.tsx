import { useState, useMemo, useRef, useEffect } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { Search, BookOpen, ChevronRight } from 'lucide-react'
import type { ThinkingStep, ActivityStep, MetadataEventData } from '../../types/api'
import { calculateTotalDuration } from '../../utils/duration'
import { buildCollapsedSummaryParts } from '../../lib/thinking/summary'
import ActivityList from './ActivityList'
import ThinkingExpandedList from './ThinkingExpandedList'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { pulseVariants, fadeIn, transitions } from '../../lib/animations'
import { STEP_ICONS, STEP_ANIMATION_VARIANTS } from '../../lib/thinking/constants'

interface ThinkingTimelineProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
  metadata?: MetadataEventData
}

function StreamingHeader({ steps, reduceMotion }: { steps: ThinkingStep[]; reduceMotion: boolean | null }) {
  const runningStep = steps.findLast((s) => s.status === 'running')
  const Icon = runningStep ? STEP_ICONS[runningStep.kind] : Search
  const variants = runningStep
    ? STEP_ANIMATION_VARIANTS[runningStep.kind]
    : pulseVariants

  return (
    <div className="flex items-center gap-2">
      <motion.div
        key={runningStep?.kind ?? 'default'}
        variants={reduceMotion ? undefined : variants}
        animate="animate"
      >
        <Icon className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
      </motion.div>
      <span className="text-sm font-display italic font-normal text-amber-800">Researching...</span>
    </div>
  )
}

export default function ThinkingTimeline({ steps, isStreaming = false, metadata }: ThinkingTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [showExpandedAfterStream, setShowExpandedAfterStream] = useState(false)
  const prevIsStreaming = useRef(isStreaming)
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (prevIsStreaming.current && !isStreaming) {
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

  const activitySteps = useMemo(
    () => steps.filter((s): s is ActivityStep => !s.isInternal),
    [steps]
  )

  const totalDuration = useMemo(() => calculateTotalDuration(steps), [steps])

  const summaryParts = useMemo(
    () => buildCollapsedSummaryParts(activitySteps, totalDuration),
    [activitySteps, totalDuration]
  )

  if (steps.length === 0) {
    return null
  }

  return (
    <AnimatePresence mode="wait">
      {isStreaming ? (
        <motion.div
          key="streaming"
          className="p-4 border-l-2 border-amber-600/70 bg-stone-50/30 space-y-3"
          variants={fadeIn}
          initial="initial"
          animate="animate"
          exit={{ opacity: 0 }}
          transition={transitions.fast}
          style={{ contain: 'layout' }}
        >
          <StreamingHeader steps={steps} reduceMotion={shouldReduceMotion} />

          <ActivityList steps={activitySteps} isStreaming />
        </motion.div>
      ) : (
        <motion.div
          key="accordion"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={transitions.fast}
          className="border-l-2 border-stone-200 overflow-hidden"
        >
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-stone-50 transition-colors duration-150"
          >
            <div className="flex items-center gap-2.5">
              <BookOpen className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
              <span className="text-sm text-stone-600">
                {isExpanded ? 'Hide' : 'View'} reasoning
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-display italic font-normal text-stone-500">
                {summaryParts.text}
              </span>
              <span className="font-mono text-xs text-stone-400">
                {'\u2014'} {summaryParts.duration}
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
              <ThinkingExpandedList steps={steps} totalDuration={totalDuration} metadata={metadata} />
            </div>
          </AnimatedCollapse>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

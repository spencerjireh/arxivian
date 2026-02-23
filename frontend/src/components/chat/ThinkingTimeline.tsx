import { useState, useMemo, useRef, useEffect } from 'react'
import { motion, useReducedMotion, AnimatePresence } from 'framer-motion'
import { Search, BookOpen, ChevronRight } from 'lucide-react'
import type { ThinkingStep, ActivityStep, MetadataEventData } from '../../types/api'
import { calculateTotalDuration } from '../../utils/duration'
import { buildCollapsedSummaryParts } from '../../lib/thinking/summary'
import ActivityList from './ActivityList'
import ThinkingExpandedList from './ThinkingExpandedList'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import {
  pulseVariants,
  fadeIn,
  crossfadeStep,
  bgFadeIn,
  transitions,
} from '../../lib/animations'
import { STEP_ICONS, STEP_ANIMATION_VARIANTS } from '../../lib/thinking/constants'

interface ThinkingTimelineProps {
  steps: ThinkingStep[]
  isStreaming?: boolean
  metadata?: MetadataEventData
}

function LatestStepDisplay({
  step,
  reduceMotion,
}: {
  step: ActivityStep | undefined
  reduceMotion: boolean | null
}) {
  const Icon = step ? STEP_ICONS[step.kind] : Search
  const variants = step ? STEP_ANIMATION_VARIANTS[step.kind] : pulseVariants

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={step?.id ?? 'default'}
        className="flex items-center gap-2"
        variants={reduceMotion ? undefined : crossfadeStep}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={transitions.fast}
      >
        <motion.div
          variants={reduceMotion ? undefined : variants}
          animate="animate"
        >
          <Icon className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
        </motion.div>
        <span className="text-sm font-display italic font-normal text-amber-800">
          {step?.message ?? 'Researching...'}
        </span>
      </motion.div>
    </AnimatePresence>
  )
}

export default function ThinkingTimeline({ steps, isStreaming = false, metadata }: ThinkingTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [streamExpanded, setStreamExpanded] = useState(false)
  const prevIsStreaming = useRef(isStreaming)
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (prevIsStreaming.current && !isStreaming) {
      queueMicrotask(() => setStreamExpanded(false))
    }
    prevIsStreaming.current = isStreaming
  }, [isStreaming])

  const activitySteps = useMemo(
    () => steps.filter((s): s is ActivityStep => !s.isInternal),
    [steps]
  )

  const latestStep = activitySteps.length > 0 ? activitySteps[activitySteps.length - 1] : undefined
  const completedSteps = activitySteps.slice(0, -1)

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
          className="relative border-l-2 border-amber-600/70"
          variants={fadeIn}
          initial="initial"
          animate="animate"
          exit={{ opacity: 0 }}
          transition={transitions.fast}
          style={{ contain: 'layout' }}
        >
          <motion.div
            className="absolute inset-0 bg-stone-50/30 rounded-r-lg pointer-events-none"
            variants={shouldReduceMotion ? undefined : bgFadeIn}
            initial="initial"
            animate="animate"
            aria-hidden="true"
          />

          <div className="relative p-4 space-y-3">
            <div className="flex items-center justify-between">
              <LatestStepDisplay step={latestStep} reduceMotion={shouldReduceMotion} />

              {completedSteps.length > 0 && (
                <button
                  onClick={() => setStreamExpanded(!streamExpanded)}
                  className="flex items-center gap-1 text-xs text-stone-400 hover:text-stone-600 transition-colors duration-150"
                >
                  <span className="font-mono tabular-nums">{completedSteps.length}</span>
                  <motion.div
                    animate={{ rotate: streamExpanded ? 90 : 0 }}
                    transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
                  >
                    <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
                  </motion.div>
                </button>
              )}
            </div>

            <AnimatedCollapse isOpen={streamExpanded}>
              <ActivityList steps={completedSteps} isStreaming />
            </AnimatedCollapse>
          </div>
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

          <AnimatedCollapse isOpen={isExpanded}>
            <div className="px-4 pb-4 pt-1">
              <ThinkingExpandedList steps={steps} totalDuration={totalDuration} metadata={metadata} />
            </div>
          </AnimatedCollapse>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

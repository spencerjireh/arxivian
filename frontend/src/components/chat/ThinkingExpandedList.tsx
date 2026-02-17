import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { AlertCircle, ChevronRight, Clock, Eye, EyeOff, Info } from 'lucide-react'
import clsx from 'clsx'
import type { ThinkingStep, MetadataEventData } from '../../types/api'
import { getStepDuration, formatDuration } from '../../utils/duration'
import { formatDetailKey, formatDetailValue } from '../../utils/formatting'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { transitions } from '../../lib/animations'
import { useSettingsStore } from '../../stores/settingsStore'
import { STEP_ICONS, STEP_ICON_COLORS } from '../../lib/thinking/constants'
import Modal from '../ui/Modal'
import MetadataPanel from './MetadataPanel'

interface ThinkingExpandedListProps {
  steps: ThinkingStep[]
  totalDuration: number
  metadata?: MetadataEventData
}

function StepIcon({ step }: { step: ThinkingStep }) {
  if (step.status === 'error') {
    return <AlertCircle className="w-3 h-3 text-red-500" strokeWidth={1.5} />
  }
  const Icon = STEP_ICONS[step.kind]
  if (Icon) {
    const colorClass = step.isInternal ? 'text-stone-400' : STEP_ICON_COLORS[step.kind]
    return <Icon className={clsx('w-3 h-3', colorClass)} strokeWidth={1.5} />
  }
  return null
}

export default function ThinkingExpandedList({ steps, totalDuration, metadata }: ThinkingExpandedListProps) {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null)
  const [localShowInternal, setLocalShowInternal] = useState<boolean | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const shouldReduceMotion = useReducedMotion()
  const globalShowInternal = useSettingsStore((s) => s.showInternalSteps)

  const showInternal = localShowInternal ?? globalShowInternal

  const visibleSteps = showInternal ? steps : steps.filter((s) => !s.isInternal)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-stone-100">
        <span className="text-xs font-display text-stone-400">Step details</span>
        <div className="flex items-center gap-3">
          {metadata && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1.5 text-xs text-stone-400 hover:text-stone-600 transition-colors duration-150"
            >
              <Info className="w-3.5 h-3.5" strokeWidth={1.5} />
              View execution details
            </button>
          )}
          <button
            onClick={() => setLocalShowInternal(!showInternal)}
            className="flex items-center gap-1.5 text-xs text-stone-400 hover:text-stone-600 transition-colors duration-150"
          >
            {showInternal ? (
              <EyeOff className="w-3.5 h-3.5" strokeWidth={1.5} />
            ) : (
              <Eye className="w-3.5 h-3.5" strokeWidth={1.5} />
            )}
            {showInternal ? 'Hide' : 'Show'} internal steps
          </button>
        </div>
      </div>

      {metadata && (
        <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Execution Details">
          <MetadataPanel metadata={metadata} defaultExpanded />
        </Modal>
      )}

      <div className="space-y-1">
        {visibleSteps.map((step) => {
          const hasDetails = step.details && Object.keys(step.details).length > 0
          const isExpanded = expandedStepId === step.id
          const duration = getStepDuration(step)

          return (
            <div key={step.id}>
              <div
                className={clsx(
                  'flex items-center gap-3 py-2.5 px-3 rounded-lg text-sm',
                  'transition-colors duration-150',
                  hasDetails && 'cursor-pointer hover:bg-stone-50',
                  step.isInternal && 'opacity-60'
                )}
                onClick={() => hasDetails && setExpandedStepId(isExpanded ? null : step.id)}
              >
                <div
                  className={clsx(
                    'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0',
                    step.status === 'complete' ? 'bg-stone-50' : 'bg-red-100'
                  )}
                >
                  <StepIcon step={step} />
                </div>

                <span className="text-stone-700 font-display min-w-[80px]">
                  {step.label}
                </span>

                <span className="text-stone-500 flex-1 truncate">{step.message}</span>

                <span className="text-xs text-stone-400 font-mono tabular-nums flex-shrink-0">
                  {formatDuration(duration)}
                </span>

                {hasDetails && (
                  <motion.div
                    className="flex-shrink-0 text-stone-300"
                    animate={{ rotate: isExpanded ? 90 : 0 }}
                    transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
                  >
                    <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
                  </motion.div>
                )}
              </div>

              {hasDetails && (
                <AnimatedCollapse isOpen={isExpanded}>
                  <div className="ml-11 mr-3 mb-2">
                    <div className="bg-stone-50 rounded-lg p-3 space-y-1.5">
                      {step.details && Object.entries(step.details).map(([key, value]) => (
                        <div key={key} className="flex text-xs">
                          <span className="text-stone-400 min-w-[100px] flex-shrink-0">
                            {formatDetailKey(key)}
                          </span>
                          <span className="text-stone-600 break-words font-mono">
                            {formatDetailValue(key, value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </AnimatedCollapse>
              )}
            </div>
          )
        })}

        <div className="flex items-center gap-2 pt-3 mt-2 border-t border-stone-100 text-xs text-stone-400 px-3">
          <Clock className="w-3.5 h-3.5" strokeWidth={1.5} />
          <span className="font-display">Total processing time:</span>
          <span className="font-mono">{formatDuration(totalDuration)}</span>
        </div>
      </div>
    </div>
  )
}

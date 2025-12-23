import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'
import { formatDuration } from '../../utils/duration'
import { formatDetailKey, formatDetailValue } from '../../utils/formatting'
import { fadeInUp, transitions } from '../../lib/animations'

interface ThinkingCurrentStepProps {
  step: ThinkingStep
}

export default function ThinkingCurrentStep({ step }: ThinkingCurrentStepProps) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (step.status !== 'running') {
      return
    }

    const interval = setInterval(() => {
      setElapsed(Date.now() - step.startTime.getTime())
    }, 100)

    return () => clearInterval(interval)
  }, [step.status, step.startTime])

  const hasDetails = step.details && Object.keys(step.details).length > 0

  return (
    <motion.div
      className="bg-white rounded-lg p-4 border border-amber-100"
      variants={fadeInUp}
      initial="initial"
      animate="animate"
      transition={transitions.fast}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin" strokeWidth={1.5} />
          <span className="text-sm font-medium text-stone-700">
            {STEP_LABELS[step.step]}
          </span>
        </div>
        <span className="text-xs text-stone-400 font-mono tabular-nums">
          {formatDuration(elapsed)}
        </span>
      </div>

      <p className="text-sm text-stone-600 leading-relaxed">{step.message}</p>

      {hasDetails && step.details && (
        <div className="mt-3 pt-3 border-t border-stone-100 flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
          {Object.entries(step.details)
            .slice(0, 3)
            .map(([key, value]) => (
              <div key={key} className="flex items-center gap-1.5">
                <span className="text-stone-400">{formatDetailKey(key)}:</span>
                <span className="text-stone-600 font-mono">
                  {formatDetailValue(key, value, { maxStringLength: 60, maxArrayItems: 2 })}
                </span>
              </div>
            ))}
        </div>
      )}
    </motion.div>
  )
}

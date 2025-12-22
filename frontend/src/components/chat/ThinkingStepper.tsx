import { motion, useReducedMotion } from 'framer-motion'
import { Check, Loader2, AlertCircle } from 'lucide-react'
import type { ThinkingStep } from '../../types/api'
import { STEP_LABELS } from '../../types/api'
import { pulseVariants, scaleIn, transitions } from '../../lib/animations'

interface ThinkingStepperProps {
  steps: ThinkingStep[]
}

export default function ThinkingStepper({ steps }: ThinkingStepperProps) {
  const shouldReduceMotion = useReducedMotion()

  if (steps.length === 0) return null

  const sortedSteps = [...steps].sort((a, b) => a.order - b.order)

  const stepAnimation = shouldReduceMotion
    ? {}
    : {
        variants: scaleIn,
        initial: 'initial',
        animate: 'animate',
        transition: transitions.fast,
      }

  return (
    <div className="flex flex-col gap-2">
      {/* Desktop: horizontal stepper */}
      <div className="hidden sm:flex items-center gap-0.5">
        {sortedSteps.map((step, index) => (
          <motion.div key={step.id} className="flex items-center" {...stepAnimation}>
            <div className="flex flex-col items-center">
              <motion.div
                variants={step.status === 'running' && !shouldReduceMotion ? pulseVariants : {}}
                animate={step.status === 'running' ? 'animate' : undefined}
                className={`
                  w-7 h-7 rounded-full flex items-center justify-center
                  transition-colors duration-200
                  ${
                    step.status === 'running'
                      ? 'bg-amber-100 text-amber-600'
                      : step.status === 'complete'
                        ? 'bg-stone-800 text-white'
                        : 'bg-red-100 text-red-600'
                  }
                `}
              >
                {step.status === 'running' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
                ) : step.status === 'complete' ? (
                  <Check className="w-3.5 h-3.5" strokeWidth={2} />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5" strokeWidth={1.5} />
                )}
              </motion.div>
              <span
                className={`
                  text-xs mt-1.5 whitespace-nowrap
                  ${step.status === 'running' ? 'text-amber-700 font-medium' : 'text-stone-500'}
                `}
              >
                {STEP_LABELS[step.step]}
              </span>
            </div>

            {index < sortedSteps.length - 1 && (
              <div
                className={`
                  w-10 h-px mx-1.5 transition-colors duration-200
                  ${step.status === 'complete' ? 'bg-stone-300' : 'bg-stone-200'}
                `}
              />
            )}
          </motion.div>
        ))}
      </div>

      {/* Mobile: vertical stepper */}
      <div className="flex sm:hidden flex-col gap-0">
        {sortedSteps.map((step, index) => (
          <motion.div key={step.id} className="flex items-start gap-3" {...stepAnimation}>
            <div className="flex flex-col items-center">
              <motion.div
                variants={step.status === 'running' && !shouldReduceMotion ? pulseVariants : {}}
                animate={step.status === 'running' ? 'animate' : undefined}
                className={`
                  w-6 h-6 rounded-full flex items-center justify-center
                  transition-colors duration-200
                  ${
                    step.status === 'running'
                      ? 'bg-amber-100 text-amber-600'
                      : step.status === 'complete'
                        ? 'bg-stone-800 text-white'
                        : 'bg-red-100 text-red-600'
                  }
                `}
              >
                {step.status === 'running' ? (
                  <Loader2 className="w-3 h-3 animate-spin" strokeWidth={1.5} />
                ) : step.status === 'complete' ? (
                  <Check className="w-3 h-3" strokeWidth={2} />
                ) : (
                  <AlertCircle className="w-3 h-3" strokeWidth={1.5} />
                )}
              </motion.div>
              {index < sortedSteps.length - 1 && (
                <div
                  className={`
                    w-px h-5 transition-colors duration-200
                    ${step.status === 'complete' ? 'bg-stone-300' : 'bg-stone-200'}
                  `}
                />
              )}
            </div>

            <span
              className={`
                text-sm leading-6
                ${step.status === 'running' ? 'text-amber-700 font-medium' : 'text-stone-600'}
              `}
            >
              {STEP_LABELS[step.step]}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

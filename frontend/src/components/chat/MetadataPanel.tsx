import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ChevronRight, Info } from 'lucide-react'
import type { MetadataEventData } from '../../types/api'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { transitions } from '../../lib/animations'

interface MetadataPanelProps {
  metadata: MetadataEventData
}

export default function MetadataPanel({ metadata }: MetadataPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const shouldReduceMotion = useReducedMotion()

  const executionTime = (metadata.execution_time_ms / 1000).toFixed(2)

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 text-xs text-stone-400 hover:text-stone-600 transition-colors duration-150"
      >
        <Info className="w-3.5 h-3.5" strokeWidth={1.5} />
        <span>{isExpanded ? 'Hide' : 'View'} execution details</span>
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
        >
          <ChevronRight className="w-3 h-3" strokeWidth={1.5} />
        </motion.div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="mt-3 p-4 bg-stone-50 rounded-xl">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Provider</span>
              <p className="text-sm text-stone-700 font-medium mt-0.5 capitalize">
                {metadata.provider}
              </p>
            </div>

            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Model</span>
              <p className="text-sm text-stone-700 font-medium mt-0.5 font-mono text-xs">
                {metadata.model}
              </p>
            </div>

            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Duration</span>
              <p className="text-sm text-stone-700 font-medium mt-0.5 font-mono">
                {executionTime}s
              </p>
            </div>

            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Retrievals</span>
              <p className="text-sm text-stone-700 font-medium mt-0.5">
                {metadata.retrieval_attempts} attempt{metadata.retrieval_attempts !== 1 ? 's' : ''}
              </p>
            </div>

            {metadata.guardrail_score !== undefined && (
              <div>
                <span className="text-xs text-stone-400 uppercase tracking-wide">Guardrail</span>
                <p className="text-sm text-stone-700 font-medium mt-0.5 font-mono">
                  {metadata.guardrail_score}%
                </p>
              </div>
            )}

            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Turn</span>
              <p className="text-sm text-stone-700 font-medium mt-0.5">
                #{metadata.turn_number}
              </p>
            </div>
          </div>

          {metadata.rewritten_query && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <span className="text-xs text-stone-400 uppercase tracking-wide">Rewritten Query</span>
              <p className="text-sm text-stone-600 mt-1 leading-relaxed">
                {metadata.rewritten_query}
              </p>
            </div>
          )}

          {metadata.reasoning_steps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <span className="text-xs text-stone-400 uppercase tracking-wide">Reasoning</span>
              <ol className="mt-2 space-y-1.5">
                {metadata.reasoning_steps.map((step, index) => (
                  <li key={index} className="flex gap-2 text-sm text-stone-600">
                    <span className="text-stone-400 font-mono text-xs mt-0.5">
                      {index + 1}.
                    </span>
                    <span className="leading-relaxed">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {metadata.session_id && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <span className="text-xs text-stone-400 uppercase tracking-wide">Session</span>
              <p className="text-xs text-stone-500 mt-1 font-mono break-all">
                {metadata.session_id}
              </p>
            </div>
          )}
        </div>
      </AnimatedCollapse>
    </div>
  )
}

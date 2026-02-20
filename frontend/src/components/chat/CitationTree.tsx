import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { GitBranch, ChevronRight } from 'lucide-react'
import type { CitationsEventData } from '../../types/api'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { transitions } from '../../lib/animations'

interface CitationTreeProps {
  citations: CitationsEventData
}

export default function CitationTree({ citations }: CitationTreeProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const shouldReduceMotion = useReducedMotion()

  if (citations.reference_count === 0) {
    return null
  }

  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50/80 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        className="w-full px-4 py-3 text-left flex items-center gap-3 hover:bg-stone-100/60 transition-colors duration-150"
      >
        <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
          <GitBranch className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-mono text-stone-400">{citations.arxiv_id}</span>
            <span className="text-xs text-stone-300">|</span>
            <span className="text-xs text-stone-500">
              {citations.reference_count} {citations.reference_count === 1 ? 'reference' : 'references'}
            </span>
          </div>
          <p className="text-sm text-stone-700 leading-snug truncate">{citations.title}</p>
        </div>

        <motion.div
          className="flex-shrink-0 text-stone-300"
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
        >
          <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
        </motion.div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="px-4 pb-4 pt-1">
          <div className="ml-11 border-l-2 border-stone-200 pl-3 space-y-1.5">
            {citations.references.map((ref, index) => (
              <div
                key={`${citations.arxiv_id}-ref-${index}`}
                className="text-sm text-stone-600 leading-relaxed flex items-start gap-2"
              >
                <span className="text-xs font-mono text-stone-400 mt-0.5 shrink-0">
                  {index + 1}.
                </span>
                <span>{ref}</span>
              </div>
            ))}
          </div>
        </div>
      </AnimatedCollapse>
    </div>
  )
}

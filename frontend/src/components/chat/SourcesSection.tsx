import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { Variants } from 'framer-motion'
import { ChevronRight, FileText } from 'lucide-react'
import type { SourceInfo } from '../../types/api'
import { transitions } from '../../lib/animations'

import SourceCard from './SourceCard'

interface SourcesSectionProps {
  sources: SourceInfo[]
  shouldReduceMotion: boolean
}

const MAX_STACKED = 3
const STACK_OFFSET = 8 // px between each stacked row
const ROW_HEIGHT = 68 // height of a compact row (py-3 + content + border)

const noMotion = { duration: 0 }

export default function SourcesSection({ sources, shouldReduceMotion }: SourcesSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (sources.length === 1) {
    return (
      <div className="mt-6 pt-6 border-t border-stone-100">
        <h4 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
          Sources
        </h4>
        <SourceCard source={sources[0]} />
      </div>
    )
  }

  const visibleStackCount = Math.min(sources.length, MAX_STACKED)
  const extraCount = sources.length - MAX_STACKED
  // Container height: first card full height + offsets for stacked cards behind it
  const stackHeight = ROW_HEIGHT + (visibleStackCount - 1) * STACK_OFFSET + (extraCount > 0 ? 20 : 0)

  const expandedContainer: Variants = {
    initial: { opacity: 0 },
    animate: {
      opacity: 1,
      transition: shouldReduceMotion ? noMotion : { duration: 0.2, staggerChildren: 0.04 },
    },
    exit: {
      opacity: 0,
      transition: shouldReduceMotion ? noMotion : { duration: 0.15 },
    },
  }

  const staggerChild: Variants = {
    initial: { opacity: 0, y: 8 },
    animate: {
      opacity: 1,
      y: 0,
      transition: shouldReduceMotion ? noMotion : { duration: 0.2 },
    },
  }

  const stackedContainer: Variants = {
    initial: { opacity: 0 },
    animate: {
      opacity: 1,
      transition: shouldReduceMotion ? noMotion : { duration: 0.2 },
    },
    exit: {
      opacity: 0,
      transition: shouldReduceMotion ? noMotion : { duration: 0.15 },
    },
  }

  return (
    <div className="mt-6 pt-6 border-t border-stone-100">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 group mb-3"
      >
        <motion.div
          className="text-stone-300"
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
        >
          <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />
        </motion.div>
        <h4 className="text-xs font-medium text-stone-400 uppercase tracking-wider group-hover:text-stone-500 transition-colors duration-150">
          Sources ({sources.length})
        </h4>
      </button>

      <motion.div
        animate={{ height: isExpanded ? 'auto' : stackHeight }}
        transition={shouldReduceMotion ? noMotion : transitions.slow}
        style={{ overflow: 'hidden' }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {isExpanded ? (
            <motion.div
              key="expanded"
              className="space-y-2"
              variants={expandedContainer}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {sources.map((source, index) => (
                <motion.div
                  key={`${source.arxiv_id}-${index}`}
                  variants={staggerChild}
                >
                  <SourceCard source={source} />
                </motion.div>
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="stacked"
              variants={stackedContainer}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <button
                onClick={() => setIsExpanded(true)}
                className="w-full text-left group/stack"
                style={{ height: stackHeight }}
              >
                <div className="relative" style={{ height: stackHeight }}>
                  {sources.slice(0, MAX_STACKED).map((source, index) => (
                    <CompactSourceRow
                      key={`${source.arxiv_id}-${index}`}
                      source={source}
                      stackIndex={index}
                    />
                  ))}
                  {extraCount > 0 && (
                    <span
                      className="absolute left-0 text-xs text-stone-400"
                      style={{ top: ROW_HEIGHT + (visibleStackCount - 1) * STACK_OFFSET + 4 }}
                    >
                      +{extraCount} more
                    </span>
                  )}
                </div>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

// -- Compact row (mirrors SourceCard collapsed header markup) --

interface CompactSourceRowProps {
  source: SourceInfo
  stackIndex: number
}

function CompactSourceRow({ source, stackIndex }: CompactSourceRowProps) {
  const relevancePercent = (source.relevance_score * 100).toFixed(0)
  const opacity = [1, 0.85, 0.7][stackIndex] ?? 0.7
  const top = stackIndex * STACK_OFFSET

  return (
    <div
      className="absolute left-0 right-0 border border-stone-100 rounded-lg bg-white px-4 py-3 flex items-start gap-3 transition-colors duration-150 group-hover/stack:border-stone-200"
      style={{
        top,
        opacity,
        zIndex: MAX_STACKED - stackIndex,
      }}
    >
      <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center flex-shrink-0 mt-0.5">
        <FileText className="w-4 h-4 text-stone-500" strokeWidth={1.5} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-mono text-stone-400">{source.arxiv_id}</span>
          <span className="text-xs text-stone-300">|</span>
          <span className="text-xs text-stone-400">{relevancePercent}% match</span>
        </div>
        <p className="text-sm text-stone-700 leading-snug line-clamp-1">{source.title}</p>
      </div>

      <div className="flex-shrink-0 text-stone-300 mt-1">
        <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
      </div>
    </div>
  )
}

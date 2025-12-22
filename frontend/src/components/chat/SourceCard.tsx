import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { ChevronRight, ExternalLink, FileText, Check, AlertTriangle } from 'lucide-react'
import type { SourceInfo } from '../../types/api'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import { transitions } from '../../lib/animations'

interface SourceCardProps {
  source: SourceInfo
}

export default function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const shouldReduceMotion = useReducedMotion()

  const relevancePercent = (source.relevance_score * 100).toFixed(0)

  return (
    <div className="border border-stone-100 rounded-lg overflow-hidden transition-colors duration-150 hover:border-stone-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left flex items-start gap-3 hover:bg-stone-50 transition-colors duration-150"
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
          <p className="text-sm text-stone-700 leading-snug line-clamp-2">{source.title}</p>
        </div>

        <motion.div
          className="flex-shrink-0 text-stone-300 mt-1"
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : transitions.fast}
        >
          <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
        </motion.div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="px-4 pb-4 pt-1">
          <div className="ml-11 space-y-3">
            <div>
              <span className="text-xs text-stone-400 uppercase tracking-wide">Authors</span>
              <p className="text-sm text-stone-600 mt-0.5 leading-relaxed">
                {source.authors.join(', ')}
              </p>
            </div>

            {source.published_date && (
              <div>
                <span className="text-xs text-stone-400 uppercase tracking-wide">Published</span>
                <p className="text-sm text-stone-600 mt-0.5">{source.published_date}</p>
              </div>
            )}

            <div className="flex items-center gap-4">
              <div>
                <span className="text-xs text-stone-400 uppercase tracking-wide">Relevance</span>
                <div className="flex items-center gap-2 mt-1">
                  <div className="w-24 h-1.5 bg-stone-100 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-stone-600 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${relevancePercent}%` }}
                      transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.5, ease: 'easeOut' }}
                    />
                  </div>
                  <span className="text-xs font-mono text-stone-500">{relevancePercent}%</span>
                </div>
              </div>

              {source.was_graded_relevant !== undefined && (
                <div className="flex items-center gap-1.5">
                  {source.was_graded_relevant ? (
                    <>
                      <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                        <Check className="w-3 h-3 text-green-600" strokeWidth={2} />
                      </div>
                      <span className="text-xs text-green-700">Verified relevant</span>
                    </>
                  ) : (
                    <>
                      <div className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center">
                        <AlertTriangle className="w-3 h-3 text-amber-600" strokeWidth={2} />
                      </div>
                      <span className="text-xs text-amber-700">Low confidence</span>
                    </>
                  )}
                </div>
              )}
            </div>

            <a
              href={source.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-stone-600 hover:text-stone-900 transition-colors duration-150"
            >
              <ExternalLink className="w-3.5 h-3.5" strokeWidth={1.5} />
              View PDF
            </a>
          </div>
        </div>
      </AnimatedCollapse>
    </div>
  )
}

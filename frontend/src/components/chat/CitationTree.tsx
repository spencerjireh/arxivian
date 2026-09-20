import { useState } from 'react'
import { GitBranch, ChevronRight } from 'lucide-react'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import type { CitationsEventData } from '../../types/api'

interface CitationTreeProps {
  citations: CitationsEventData
}

export default function CitationTree({ citations }: CitationTreeProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (citations.reference_count === 0) {
    return null
  }

  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-stone-50/80">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-stone-100/60"
      >
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-amber-50">
          <GitBranch className="h-4 w-4 text-amber-600" strokeWidth={1.5} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-center gap-2">
            <span className="font-mono text-xs text-stone-400">{citations.arxiv_id}</span>
            <span className="text-xs text-stone-300">|</span>
            <span className="text-xs text-stone-500">
              {citations.reference_count}{' '}
              {citations.reference_count === 1 ? 'reference' : 'references'}
            </span>
          </div>
          <p className="truncate text-sm leading-snug text-stone-700">{citations.title}</p>
        </div>

        <div className="chevron-rotate flex-shrink-0 text-stone-300" data-expanded={isExpanded}>
          <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
        </div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="px-4 pt-1 pb-4">
          <div className="ml-11 space-y-1.5 border-l-2 border-stone-200 pl-3">
            {citations.references.map((ref, index) => (
              <div
                key={`${citations.arxiv_id}-ref-${index}`}
                className="flex items-start gap-2 text-sm leading-relaxed text-stone-600"
              >
                <span className="mt-0.5 shrink-0 font-mono text-xs text-stone-400">
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

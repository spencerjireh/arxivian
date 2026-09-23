// Scoped chat: one retrieved source (backend schemas/stream.py::SourceInfo).
import { useState } from 'react'
import { ChevronRight, ExternalLink, FileText, Check, AlertTriangle } from 'lucide-react'
import { AnimatedCollapse } from '@/components/ui/AnimatedCollapse'
import type { SourceInfo } from '@/types/api'

interface SourceCardProps {
  source: SourceInfo
}

export default function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const relevancePercent = (source.relevance_score * 100).toFixed(0)

  return (
    <div className="overflow-hidden rounded-lg border border-stone-100 transition-colors duration-150 hover:border-stone-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-stone-50"
      >
        <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-stone-100">
          <FileText className="h-4 w-4 text-stone-500" strokeWidth={1.5} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-mono text-xs text-stone-400">{source.arxiv_id}</span>
            <span className="text-xs text-stone-300">|</span>
            <span className="text-xs text-stone-400">{relevancePercent}% match</span>
          </div>
          <p className="line-clamp-2 text-sm leading-snug text-stone-700">{source.title}</p>
        </div>

        <div
          className="chevron-rotate mt-1 flex-shrink-0 text-stone-300"
          data-expanded={isExpanded}
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
        </div>
      </button>

      <AnimatedCollapse isOpen={isExpanded}>
        <div className="px-4 pt-1 pb-4">
          <div className="ml-11 space-y-3">
            <div>
              <span className="text-xs tracking-wide text-stone-400 uppercase">Authors</span>
              <p className="mt-0.5 text-sm leading-relaxed text-stone-600">
                {source.authors.join(', ')}
              </p>
            </div>

            {source.published_date && (
              <div>
                <span className="text-xs tracking-wide text-stone-400 uppercase">Published</span>
                <p className="mt-0.5 text-sm text-stone-600">{source.published_date}</p>
              </div>
            )}

            <div className="flex items-center gap-4">
              <div>
                <span className="text-xs tracking-wide text-stone-400 uppercase">Relevance</span>
                <div className="mt-1 flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-stone-100">
                    <div
                      className="h-full rounded-full bg-stone-600 transition-[width] duration-500 ease-out"
                      style={{ width: `${relevancePercent}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-stone-500">{relevancePercent}%</span>
                </div>
              </div>

              {source.was_graded_relevant !== undefined && (
                <div className="flex items-center gap-1.5">
                  {source.was_graded_relevant ? (
                    <>
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100">
                        <Check className="h-3 w-3 text-green-600" strokeWidth={2} />
                      </div>
                      <span className="text-xs text-green-700">Verified relevant</span>
                    </>
                  ) : (
                    <>
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-100">
                        <AlertTriangle className="h-3 w-3 text-amber-600" strokeWidth={2} />
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
              className="inline-flex items-center gap-1.5 text-sm text-stone-600 transition-colors duration-150 hover:text-stone-900"
            >
              <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
              View PDF
            </a>
          </div>
        </div>
      </AnimatedCollapse>
    </div>
  )
}

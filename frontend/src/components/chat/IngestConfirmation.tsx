import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BookMarked, Check, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import type { ConfirmIngestEventData } from '../../types/api'

interface IngestConfirmationProps {
  proposal: ConfirmIngestEventData
  onConfirm: (approved: boolean, selectedIds: string[]) => void
  isResolved?: boolean
  isIngesting?: boolean
}

function truncateAuthors(authors: string[], max = 3): string {
  if (authors.length <= max) return authors.join(', ')
  return `${authors.slice(0, max).join(', ')} +${authors.length - max} more`
}

export default function IngestConfirmation({
  proposal,
  onConfirm,
  isResolved = false,
  isIngesting = false,
}: IngestConfirmationProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(proposal.papers.map((p) => p.arxiv_id))
  )

  const isInteractive = !isResolved && !isIngesting

  const togglePaper = (arxivId: string) => {
    if (!isInteractive) return
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(arxivId)) {
        next.delete(arxivId)
      } else {
        next.add(arxivId)
      }
      return next
    })
  }

  const toggleAll = () => {
    if (!isInteractive) return
    if (selectedIds.size === proposal.papers.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(proposal.papers.map((p) => p.arxiv_id)))
    }
  }

  const handleConfirm = () => {
    if (selectedIds.size === 0) return
    onConfirm(true, Array.from(selectedIds))
  }

  const handleSkip = () => {
    onConfirm(false, [])
  }

  const selectedCount = selectedIds.size
  const allSelected = selectedCount === proposal.papers.length

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
      className="my-4 rounded-xl border border-stone-200 bg-stone-50/80 overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-stone-200/80 bg-stone-100/50">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-amber-700/10 flex items-center justify-center">
            <BookMarked className="w-3.5 h-3.5 text-amber-700" strokeWidth={1.5} />
          </div>
          <div>
            <h4 className="text-sm font-medium text-stone-700">
              {proposal.papers.length} {proposal.papers.length === 1 ? 'paper' : 'papers'} found
            </h4>
          </div>
        </div>

        {isInteractive && (
          <button
            type="button"
            onClick={toggleAll}
            className="text-xs text-stone-500 hover:text-stone-700 transition-colors"
          >
            {allSelected ? 'Deselect all' : 'Select all'}
          </button>
        )}

        {isIngesting && (
          <div className="flex items-center gap-1.5 text-xs text-amber-700">
            <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={2} />
            <span>Adding to library...</span>
          </div>
        )}

        {isResolved && !isIngesting && (
          <div className="flex items-center gap-1.5 text-xs text-green-700">
            <Check className="w-3.5 h-3.5" strokeWidth={2} />
            <span>Added to library</span>
          </div>
        )}
      </div>

      {/* Paper list */}
      <div className="divide-y divide-stone-200/60">
        {proposal.papers.map((paper, index) => {
          const isSelected = selectedIds.has(paper.arxiv_id)

          return (
            <motion.div
              key={paper.arxiv_id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: index * 0.04, duration: 0.2 }}
              className={clsx(
                'flex gap-3 px-4 py-3 transition-colors',
                isInteractive && 'cursor-pointer hover:bg-stone-100/60',
                !isInteractive && 'opacity-75',
              )}
              onClick={() => togglePaper(paper.arxiv_id)}
            >
              {/* Checkbox */}
              <div className="pt-0.5 shrink-0">
                <div
                  className={clsx(
                    'w-4 h-4 rounded border transition-all duration-150',
                    isSelected
                      ? 'bg-amber-700 border-amber-700'
                      : 'border-stone-300 bg-white',
                    !isInteractive && 'opacity-60',
                  )}
                >
                  <AnimatePresence>
                    {isSelected && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        exit={{ scale: 0 }}
                        transition={{ duration: 0.15 }}
                        className="flex items-center justify-center w-full h-full"
                      >
                        <Check className="w-3 h-3 text-white" strokeWidth={3} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Paper details */}
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-stone-800 leading-snug line-clamp-2">
                  {paper.title}
                </p>
                <p className="mt-1 text-xs text-stone-500">
                  {truncateAuthors(paper.authors)}
                  {paper.published_date && (
                    <span className="text-stone-400">
                      {' -- '}{paper.published_date.slice(0, 4)}
                    </span>
                  )}
                </p>
                <p className="mt-1 text-xs text-stone-400 leading-relaxed line-clamp-2">
                  {paper.abstract}
                </p>
                <p className="mt-1 text-[11px] font-mono text-stone-400">
                  {paper.arxiv_id}
                </p>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Actions */}
      {isInteractive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.2 }}
          className="flex items-center justify-end gap-2 px-4 py-3 border-t border-stone-200/80 bg-stone-100/30"
        >
          <button
            type="button"
            onClick={handleSkip}
            className={clsx(
              'px-3 py-1.5 text-sm text-stone-500 rounded-lg',
              'hover:bg-stone-200/60 hover:text-stone-700 transition-colors',
            )}
          >
            Skip
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={selectedCount === 0}
            className={clsx(
              'px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors',
              selectedCount > 0
                ? 'bg-amber-700 text-white hover:bg-amber-800'
                : 'bg-stone-200 text-stone-400 cursor-not-allowed',
            )}
          >
            Add {selectedCount > 0 ? selectedCount : ''} to library
          </button>
        </motion.div>
      )}
    </motion.div>
  )
}

import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Trash2, ExternalLink } from 'lucide-react'
import { transitions } from '../../lib/animations'
import type { PaperListItem } from '../../types/api'

interface PaperCardProps {
  paper: PaperListItem
  onDelete: (arxivId: string) => void
  isDeleting: boolean
}

function formatAuthors(authors: string[]): string {
  if (authors.length <= 3) return authors.join(', ')
  return `${authors.slice(0, 3).join(', ')} +${authors.length - 3} more`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function PaperCard({ paper, onDelete, isDeleting }: PaperCardProps) {
  const shouldReduceMotion = useReducedMotion()
  const [showConfirm, setShowConfirm] = useState(false)

  const handleDelete = () => {
    onDelete(paper.arxiv_id)
  }

  return (
    <div className="group bg-white border border-stone-200 rounded-xl p-5 transition-colors hover:border-stone-300">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs bg-stone-100 px-2 py-0.5 rounded text-stone-600">
            {paper.arxiv_id}
          </span>
          <span
            className={`w-2 h-2 rounded-full ${paper.pdf_processed ? 'bg-emerald-400' : 'bg-amber-400'}`}
            title={paper.pdf_processed ? 'Processed' : 'Not processed'}
          />
        </div>
        {showConfirm ? (
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="px-2 py-1 text-xs font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 transition-colors disabled:opacity-50"
            >
              {isDeleting ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              disabled={isDeleting}
              className="px-2 py-1 text-xs text-stone-500 rounded-md hover:bg-stone-100 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        ) : (
          <motion.button
            onClick={() => setShowConfirm(true)}
            whileHover={shouldReduceMotion ? {} : { scale: 1.1 }}
            whileTap={shouldReduceMotion ? {} : { scale: 0.9 }}
            transition={transitions.fast}
            className="
              p-1.5 rounded-md opacity-0 group-hover:opacity-100
              text-stone-400 hover:text-red-600 hover:bg-red-50
              transition-[opacity,color,background-color] duration-150
              flex-shrink-0
            "
            aria-label="Delete paper"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          </motion.button>
        )}
      </div>

      <h3 className="font-display text-lg font-semibold text-stone-900 leading-snug line-clamp-2 mb-1.5">
        {paper.title}
      </h3>

      <p className="text-sm text-stone-500 truncate mb-2">
        {formatAuthors(paper.authors)}
      </p>

      <p className="text-sm text-stone-600 leading-relaxed line-clamp-3 mb-3">
        {paper.abstract}
      </p>

      {paper.categories.length > 0 && (
        <div className="inline-flex flex-wrap gap-1.5 mb-3">
          {paper.categories.map((cat) => (
            <span
              key={cat}
              className="text-xs px-2 py-0.5 bg-stone-100 text-stone-600 rounded-full"
            >
              {cat}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-stone-100">
        <span className="text-xs text-stone-400">
          {formatDate(paper.published_date)}
        </span>
        <a
          href={paper.pdf_url}
          target="_blank"
          className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-700 transition-colors"
        >
          PDF
          <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
        </a>
      </div>
    </div>
  )
}

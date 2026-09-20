import { ExternalLink } from 'lucide-react'
import clsx from 'clsx'
import { formatAuthors, formatDate } from '../../utils/formatting'
import type { PaperListItem } from '../../types/api'

interface PaperCardProps {
  paper: PaperListItem
}

export default function PaperCard({ paper }: PaperCardProps) {
  return (
    <div className="group rounded-xl border border-stone-200 bg-white p-5 transition-colors hover:border-stone-300">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="rounded bg-stone-100 px-2 py-0.5 font-mono text-xs text-stone-600">
            {paper.arxiv_id}
          </span>
          <span
            className={clsx(
              'h-2 w-2 rounded-full',
              paper.pdf_processed ? 'bg-emerald-400' : 'bg-amber-400'
            )}
            title={paper.pdf_processed ? 'Processed' : 'Not processed'}
          />
        </div>
      </div>

      <h3 className="font-display mb-1.5 line-clamp-2 text-lg leading-snug font-semibold text-stone-900">
        {paper.title}
      </h3>

      <p className="mb-2 truncate text-sm text-stone-500">{formatAuthors(paper.authors)}</p>

      <p className="mb-3 line-clamp-3 text-sm leading-relaxed text-stone-600">{paper.abstract}</p>

      {paper.categories.length > 0 && (
        <div className="mb-3 inline-flex flex-wrap gap-1.5">
          {paper.categories.map((cat) => (
            <span
              key={cat}
              className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600"
            >
              {cat}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-stone-100 pt-2">
        <span className="text-xs text-stone-400">{formatDate(paper.published_date)}</span>
        <a
          href={paper.pdf_url}
          target="_blank"
          className="inline-flex items-center gap-1 text-xs text-stone-500 transition-colors hover:text-stone-700"
        >
          PDF
          <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
        </a>
      </div>
    </div>
  )
}

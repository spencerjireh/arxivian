import { useState, useEffect, useMemo } from 'react'
import { Loader2, BookOpen, ChevronLeft, ChevronRight } from 'lucide-react'
import { usePapers, useDeletePaper } from '../api/papers'
import PaperCard from '../components/library/PaperCard'
import Button from '../components/ui/Button'
import type { PaperListParams } from '../types/api'

type ProcessedFilter = 'all' | 'processed' | 'unprocessed'
type SortBy = 'created_at' | 'published_date'
type SortOrder = 'desc' | 'asc'

const LIMIT = 20

export default function LibraryPage() {
  const [offset, setOffset] = useState(0)
  const [categoryInput, setCategoryInput] = useState('')
  const [debouncedCategory, setDebouncedCategory] = useState('')
  const [processedFilter, setProcessedFilter] = useState<ProcessedFilter>('all')
  const [sortBy, setSortBy] = useState<SortBy>('created_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // Debounce category input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedCategory(categoryInput)
      setOffset(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [categoryInput])

  const params = useMemo<PaperListParams>(() => {
    const p: PaperListParams = {
      offset,
      limit: LIMIT,
      sort_by: sortBy,
      sort_order: sortOrder,
    }
    if (debouncedCategory) p.category = debouncedCategory
    if (processedFilter === 'processed') p.processed_only = true
    if (processedFilter === 'unprocessed') p.processed_only = false
    return p
  }, [offset, debouncedCategory, processedFilter, sortBy, sortOrder])

  const { data, isLoading, error } = usePapers(params)
  const deletePaper = useDeletePaper()

  const handleDelete = (arxivId: string) => {
    deletePaper.mutate(arxivId)
  }

  const total = data?.total ?? 0
  const hasPages = total > LIMIT
  const hasPrev = offset > 0
  const hasNext = offset + LIMIT < total

  const processedOptions: { value: ProcessedFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'processed', label: 'Processed' },
    { value: 'unprocessed', label: 'Unprocessed' },
  ]

  const selectClass =
    'px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150'

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Page header */}
      <div className="px-6 pt-6 pb-4">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-2xl font-semibold text-stone-900">Library</h1>
          {data && (
            <span className="text-sm text-stone-400 font-mono">
              {total} paper{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Filter bar */}
      <div className="px-6 pb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={categoryInput}
          onChange={(e) => setCategoryInput(e.target.value)}
          placeholder="Filter by category..."
          className={`${selectClass} w-48`}
        />

        <div className="inline-flex rounded-lg overflow-hidden border border-stone-200">
          {processedOptions.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => {
                setProcessedFilter(value)
                setOffset(0)
              }}
              className={`px-3 py-2 text-sm transition-colors duration-150 ${
                processedFilter === value
                  ? 'bg-stone-900 text-white'
                  : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <select
          value={`${sortBy}:${sortOrder}`}
          onChange={(e) => {
            const [sb, so] = e.target.value.split(':') as [SortBy, SortOrder]
            setSortBy(sb)
            setSortOrder(so)
            setOffset(0)
          }}
          className={selectClass}
        >
          <option value="created_at:desc">Newest added</option>
          <option value="created_at:asc">Oldest added</option>
          <option value="published_date:desc">Recently published</option>
          <option value="published_date:asc">Earliest published</option>
        </select>
      </div>

      {/* Paper grid */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-24">
            <p className="text-sm text-stone-500">Unable to load papers</p>
          </div>
        ) : !data || data.papers.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mb-3">
              <BookOpen className="w-5 h-5 text-stone-400" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-stone-700">No papers yet</p>
            <p className="text-sm text-stone-400 mt-1">
              Papers will appear here once ingested via chat
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.papers.map((paper) => (
              <PaperCard
                key={paper.arxiv_id}
                paper={paper}
                onDelete={handleDelete}
                isDeleting={
                  deletePaper.isPending && deletePaper.variables === paper.arxiv_id
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {hasPages && (
        <div className="px-6 py-3 border-t border-stone-200 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            disabled={!hasPrev}
            leftIcon={<ChevronLeft className="w-4 h-4" strokeWidth={1.5} />}
          >
            Previous
          </Button>
          <span className="text-xs text-stone-400">
            {Math.min(offset + 1, total)}-{Math.min(offset + LIMIT, total)} of {total}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOffset(offset + LIMIT)}
            disabled={!hasNext}
            rightIcon={<ChevronRight className="w-4 h-4" strokeWidth={1.5} />}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  )
}

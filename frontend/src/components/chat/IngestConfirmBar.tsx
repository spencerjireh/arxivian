import { useState } from 'react'
import clsx from 'clsx'
import { BookMarked } from 'lucide-react'
import { useChatStore } from '../../stores/chatStore'

interface IngestConfirmBarProps {
  onConfirm: (approved: boolean, selectedIds: string[]) => void
}

export default function IngestConfirmBar({ onConfirm }: IngestConfirmBarProps) {
  const ingestProposal = useChatStore((s) => s.ingestProposal)
  const selectedIngestIds = useChatStore((s) => s.selectedIngestIds)
  const isIngesting = useChatStore((s) => s.isIngesting)
  const [submitted, setSubmitted] = useState(false)

  if (!ingestProposal) return null

  const selectedCount = selectedIngestIds?.size ?? 0
  const totalCount = ingestProposal.papers.length
  const isDisabled = submitted || isIngesting

  const handleAdd = () => {
    if (isDisabled || selectedCount === 0) return
    setSubmitted(true)
    onConfirm(true, Array.from(selectedIngestIds ?? []))
  }

  const handleCancel = () => {
    if (isDisabled) return
    setSubmitted(true)
    onConfirm(false, [])
  }

  return (
    <div className="chat-input-fade relative z-10">
      <div className="max-w-5xl mx-auto px-6 py-4">
        <div
          className={clsx(
            'flex items-center justify-between gap-3',
            'rounded-xl border border-stone-200 bg-stone-50 px-4 py-3',
          )}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-amber-700/10 flex items-center justify-center shrink-0">
              <BookMarked className="w-3.5 h-3.5 text-amber-700" strokeWidth={1.5} />
            </div>
            <span className="text-sm text-stone-600 truncate">
              {selectedCount} of {totalCount} {totalCount === 1 ? 'paper' : 'papers'} selected
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isDisabled}
              className={clsx(
                'px-3 py-1.5 text-sm text-stone-500 rounded-lg transition-colors',
                isDisabled
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-stone-200/60 hover:text-stone-700',
              )}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleAdd}
              disabled={isDisabled || selectedCount === 0}
              className={clsx(
                'px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors',
                !isDisabled && selectedCount > 0
                  ? 'bg-amber-700 text-white hover:bg-amber-800'
                  : 'bg-stone-200 text-stone-400 cursor-not-allowed',
              )}
            >
              Add {selectedCount > 0 ? selectedCount : ''} to library
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

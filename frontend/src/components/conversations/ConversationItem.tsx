// Single conversation list item component

import { Loader2, Trash2, ArrowUpRight } from 'lucide-react'
import type { ConversationListItem } from '../../types/api'

interface ConversationItemProps {
  conversation: ConversationListItem
  onClick: () => void
  onDelete: () => void
  isDeleting?: boolean
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 1) + '\u2026'
}

export default function ConversationItem({
  conversation,
  onClick,
  onDelete,
  isDeleting,
}: ConversationItemProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete()
  }

  return (
    <div
      onClick={onClick}
      className="group relative px-6 py-4 hover:bg-stone-50 cursor-pointer transition-colors duration-150"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Last query preview */}
          <p className="text-stone-800 leading-relaxed mb-2 pr-8">
            {conversation.last_query
              ? truncate(conversation.last_query, 100)
              : 'No messages yet'}
          </p>

          {/* Metadata row */}
          <div className="flex items-center gap-3 text-xs text-stone-400">
            <span className="font-mono">{truncate(conversation.session_id, 8)}</span>
            <span className="w-1 h-1 rounded-full bg-stone-300" />
            <span>{conversation.turn_count} {conversation.turn_count === 1 ? 'turn' : 'turns'}</span>
            <span className="w-1 h-1 rounded-full bg-stone-300" />
            <span>{formatRelativeTime(conversation.updated_at)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="p-2 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors duration-150 disabled:opacity-50"
            title="Delete conversation"
          >
            {isDeleting ? (
              <Loader2 className="w-4 h-4 animate-spin" strokeWidth={1.5} />
            ) : (
              <Trash2 className="w-4 h-4" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>

      {/* Arrow indicator on hover */}
      <ArrowUpRight
        className="absolute right-6 top-4 w-4 h-4 text-stone-300 opacity-0 group-hover:opacity-100 transition-opacity duration-150"
        strokeWidth={1.5}
      />
    </div>
  )
}

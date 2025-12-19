// Single conversation list item component

import { Loader2, Trash2 } from 'lucide-react'
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
  return date.toLocaleDateString()
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 3) + '...'
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
      className="group px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 transition-colors duration-200"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Session ID (truncated) */}
          <p className="text-xs font-mono text-gray-400">
            {truncate(conversation.session_id, 12)}
          </p>

          {/* Last query preview */}
          <p className="text-sm text-gray-700 mt-1 truncate">
            {conversation.last_query || 'No messages yet'}
          </p>

          {/* Metadata row */}
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span>{conversation.turn_count} turns</span>
            <span>-</span>
            <span>{formatRelativeTime(conversation.updated_at)}</span>
          </div>
        </div>

        {/* Delete button */}
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="ml-2 p-1.5 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all duration-200 disabled:opacity-50"
          title="Delete conversation"
        >
          {isDeleting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Trash2 className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  )
}

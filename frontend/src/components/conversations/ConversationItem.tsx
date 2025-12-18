// Single conversation list item component

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
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

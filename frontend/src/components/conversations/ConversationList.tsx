// Past conversations list component

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConversations, useDeleteConversation } from '../../api/conversations'
import ConversationItem from './ConversationItem'

export default function ConversationList() {
  const navigate = useNavigate()
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useConversations(offset, limit)
  const deleteConversation = useDeleteConversation()

  const handleNavigate = (sessionId: string) => {
    navigate(`/${sessionId}`)
  }

  const handleDelete = (sessionId: string) => {
    deleteConversation.mutate(sessionId)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <svg className="w-6 h-6 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
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
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 py-8 text-center text-red-500">
        <p>Failed to load conversations</p>
        <p className="text-sm text-gray-500 mt-1">{(error as Error).message}</p>
      </div>
    )
  }

  if (!data || data.conversations.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-gray-500">
        <p>No conversations yet</p>
        <p className="text-sm mt-1">Start a new chat to begin</p>
      </div>
    )
  }

  const hasMore = offset + limit < data.total
  const hasPrev = offset > 0

  return (
    <div>
      <div className="divide-y divide-gray-100">
        {data.conversations.map((conversation) => (
          <ConversationItem
            key={conversation.session_id}
            conversation={conversation}
            onClick={() => handleNavigate(conversation.session_id)}
            onDelete={() => handleDelete(conversation.session_id)}
            isDeleting={
              deleteConversation.isPending &&
              deleteConversation.variables === conversation.session_id
            }
          />
        ))}
      </div>

      {/* Pagination */}
      {(hasMore || hasPrev) && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={!hasPrev}
            className="text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500">
            {offset + 1}-{Math.min(offset + limit, data.total)} of {data.total}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={!hasMore}
            className="text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

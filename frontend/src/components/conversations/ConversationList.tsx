// Past conversations list component

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, ChevronLeft, ChevronRight, MessageSquare } from 'lucide-react'
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
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-5 h-5 animate-spin text-stone-300" strokeWidth={1.5} />
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-6 py-12 text-center">
        <p className="text-stone-900 font-medium mb-1">Unable to load conversations</p>
        <p className="text-sm text-stone-400">{(error as Error).message}</p>
      </div>
    )
  }

  if (!data || data.conversations.length === 0) {
    return (
      <div className="px-6 py-16 text-center">
        <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mx-auto mb-4">
          <MessageSquare className="w-5 h-5 text-stone-400" strokeWidth={1.5} />
        </div>
        <p className="text-stone-900 font-medium mb-1">No conversations yet</p>
        <p className="text-sm text-stone-400">Start a new chat to begin exploring</p>
      </div>
    )
  }

  const hasMore = offset + limit < data.total
  const hasPrev = offset > 0

  return (
    <div>
      <div className="divide-y divide-stone-100 stagger-children">
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
        <div className="flex items-center justify-between px-6 py-4 border-t border-stone-100">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={!hasPrev}
            className="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 disabled:text-stone-300 disabled:cursor-not-allowed transition-colors duration-150"
          >
            <ChevronLeft className="w-4 h-4" strokeWidth={1.5} />
            Previous
          </button>
          <span className="text-xs text-stone-400 font-mono">
            {offset + 1} - {Math.min(offset + limit, data.total)} of {data.total}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={!hasMore}
            className="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 disabled:text-stone-300 disabled:cursor-not-allowed transition-colors duration-150"
          >
            Next
            <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
          </button>
        </div>
      )}
    </div>
  )
}

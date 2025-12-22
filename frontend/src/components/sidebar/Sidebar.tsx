// Main sidebar component with conversation list

import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, PanelLeftClose, Loader2, MessageSquare, ChevronUp, ChevronDown } from 'lucide-react'
import { useConversations, useDeleteConversation } from '../../api/conversations'
import { useSidebarStore } from '../../stores/sidebarStore'
import SidebarConversationItem from './SidebarConversationItem'

export default function Sidebar() {
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const close = useSidebarStore((state) => state.close)

  const [offset, setOffset] = useState(0)
  const limit = 30

  const { data, isLoading, error } = useConversations(offset, limit)
  const deleteConversation = useDeleteConversation()

  const handleNewConversation = () => {
    navigate('/new')
  }

  const handleNavigate = (id: string) => {
    navigate(`/${id}`)
  }

  const handleDelete = (id: string) => {
    deleteConversation.mutate(id, {
      onSuccess: () => {
        // If deleting the current conversation, navigate to home
        if (id === sessionId) {
          navigate('/')
        }
      },
    })
  }

  const hasMore = data ? offset + limit < data.total : false
  const hasPrev = offset > 0

  return (
    <aside className="w-72 h-screen bg-stone-50 border-r border-stone-200 flex flex-col animate-slide-in-left">
      {/* Header with logo */}
      <div className="px-4 py-5 border-b border-stone-200">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-xl font-semibold text-stone-900 tracking-tight">
            Jireh's Agent
          </h1>
          <button
            onClick={close}
            className="p-2 text-stone-400 hover:text-stone-600 hover:bg-stone-100 rounded-lg transition-colors duration-150"
            title="Close sidebar"
          >
            <PanelLeftClose className="w-5 h-5" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* New conversation button */}
      <div className="px-3 py-3">
        <button
          onClick={handleNewConversation}
          className="
            w-full flex items-center gap-2.5 px-3 py-2.5
            bg-stone-900 hover:bg-stone-800 text-white
            rounded-lg transition-colors duration-150
            text-sm font-medium
          "
        >
          <Plus className="w-4 h-4" strokeWidth={2} />
          New conversation
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-stone-500">Unable to load</p>
          </div>
        ) : !data || data.conversations.length === 0 ? (
          <div className="px-3 py-12 text-center">
            <div className="w-10 h-10 rounded-full bg-stone-100 flex items-center justify-center mx-auto mb-3">
              <MessageSquare className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
            </div>
            <p className="text-sm text-stone-500">No conversations yet</p>
          </div>
        ) : (
          <div className="space-y-1 pb-4">
            {data.conversations.map((conversation) => (
              <SidebarConversationItem
                key={conversation.session_id}
                conversation={conversation}
                isActive={conversation.session_id === sessionId}
                onClick={() => handleNavigate(conversation.session_id)}
                onDelete={() => handleDelete(conversation.session_id)}
                isDeleting={
                  deleteConversation.isPending &&
                  deleteConversation.variables === conversation.session_id
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Pagination controls */}
      {data && (hasMore || hasPrev) && (
        <div className="px-3 py-2 border-t border-stone-200">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={!hasPrev}
              className="p-1.5 text-stone-400 hover:text-stone-600 disabled:text-stone-300 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronUp className="w-4 h-4" strokeWidth={1.5} />
            </button>
            <span className="text-xs text-stone-400">
              {Math.min(offset + 1, data.total)}-{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <button
              onClick={() => setOffset(offset + limit)}
              disabled={!hasMore}
              className="p-1.5 text-stone-400 hover:text-stone-600 disabled:text-stone-300 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronDown className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}

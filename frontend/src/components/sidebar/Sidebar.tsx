import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, PanelLeftClose, Loader2, MessageSquare, ChevronUp, ChevronDown } from 'lucide-react'
import { useConversations, useDeleteConversation } from '../../api/conversations'
import { useSidebarStore } from '../../stores/sidebarStore'
import SidebarConversationItem from './SidebarConversationItem'
import Button from '../ui/Button'

export default function Sidebar() {
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const close = useSidebarStore((state) => state.close)

  const [offset, setOffset] = useState(0)
  const limit = 30

  const { data, isLoading, error } = useConversations(offset, limit)
  const deleteConversation = useDeleteConversation()

  const handleNewConversation = () => {
    navigate('/')
  }

  const handleNavigate = (id: string) => {
    navigate(`/${id}`)
  }

  const handleDelete = (id: string) => {
    deleteConversation.mutate(id, {
      onSuccess: () => {
        if (id === sessionId) {
          navigate('/')
        }
      },
    })
  }

  const hasMore = data ? offset + limit < data.total : false
  const hasPrev = offset > 0

  return (
    <div className="w-72 h-screen bg-stone-50 border-r border-stone-200 flex flex-col">
      <div className="px-4 py-5 border-b border-stone-200">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-xl font-semibold text-stone-900 tracking-tight">
            Jireh's Agent
          </h1>
          <Button
            variant="ghost"
            size="sm"
            onClick={close}
            aria-label="Close sidebar"
          >
            <PanelLeftClose className="w-5 h-5" strokeWidth={1.5} />
          </Button>
        </div>
      </div>

      <div className="px-3 py-3">
        <Button
          variant="primary"
          className="w-full !px-3 !py-1.5"
          onClick={handleNewConversation}
          leftIcon={<Plus className="w-4 h-4" strokeWidth={2} />}
        >
          New conversation
        </Button>
      </div>

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
          <>
            <h2 className="text-xs text-stone-600 px-3 pt-8 pb-2">
              Recent conversations
            </h2>
            <div className="space-y-0.5 pb-4">
              {data.conversations.map((conversation) => (
                <div key={conversation.session_id}>
                <SidebarConversationItem
                  conversation={conversation}
                  isActive={conversation.session_id === sessionId}
                  onClick={() => handleNavigate(conversation.session_id)}
                  onDelete={() => handleDelete(conversation.session_id)}
                  isDeleting={
                    deleteConversation.isPending &&
                    deleteConversation.variables === conversation.session_id
                  }
                />
              </div>
            ))}
            </div>
          </>
        )}
      </div>

      {data && (hasMore || hasPrev) && (
        <div className="px-3 py-2 border-t border-stone-200">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={!hasPrev}
              aria-label="Previous page"
            >
              <ChevronUp className="w-4 h-4" strokeWidth={1.5} />
            </Button>
            <span className="text-xs text-stone-400">
              {Math.min(offset + 1, data.total)}-{Math.min(offset + limit, data.total)} of {data.total}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOffset(offset + limit)}
              disabled={!hasMore}
              aria-label="Next page"
            >
              <ChevronDown className="w-4 h-4" strokeWidth={1.5} />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { Plus, PanelLeftClose, Loader2, MessageSquare, BookOpen, Settings, ChevronUp, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import { useConversations, useDeleteConversation } from '../../api/conversations'
import { useSidebarStore } from '../../stores/sidebarStore'
import SidebarConversationItem from './SidebarConversationItem'
import UserMenu from './UserMenu'
import Button from '../ui/Button'
import ErrorBoundary from '../ui/ErrorBoundary'
import SectionErrorFallback from '../ui/SectionErrorFallback'
import { getUserMessage } from '../../lib/errors'
import logoIcon from '../../assets/logo-icon.png'

const navItems = [
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/library', label: 'Library', icon: BookOpen },
  { path: '/settings', label: 'Settings', icon: Settings },
] as const

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const close = useSidebarStore((state) => state.close)
  const lastSessionId = useSidebarStore((state) => state.lastSessionId)

  return (
    <div className="w-72 h-screen bg-stone-50 border-r border-stone-200 flex flex-col">
      <div className="px-4 py-5 border-b border-stone-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src={logoIcon} alt="" className="h-6 w-auto" aria-hidden="true" />
            <h1 className="font-display text-xl font-semibold text-stone-900 tracking-tight">
              Arxivian
              <span className="ml-2 text-[10px] font-mono font-normal uppercase tracking-wider text-stone-400 bg-stone-100 px-1.5 py-0.5 rounded">
                Beta
              </span>
            </h1>
          </div>
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

      <nav className="px-3 py-3 space-y-0.5">
        <Button
          variant="primary"
          size="md"
          className="w-full"
          onClick={() => navigate('/chat')}
          leftIcon={<Plus className="w-4 h-4" strokeWidth={2} />}
        >
          New conversation
        </Button>
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = path === '/chat'
            ? location.pathname.startsWith('/chat')
            : location.pathname === path
          const target = path === '/chat' && lastSessionId
            ? `/chat/${lastSessionId}`
            : path
          return (
            <Button
              key={path}
              variant="ghost"
              size="md"
              className={clsx(
                'w-full justify-start',
                isActive && 'bg-stone-100 text-stone-900 font-medium'
              )}
              onClick={() => navigate(target)}
              leftIcon={<Icon className="w-4 h-4" strokeWidth={1.5} />}
            >
              {label}
            </Button>
          )
        })}
      </nav>

      <ErrorBoundary fallback={(props) => <SectionErrorFallback {...props} />}>
        <SidebarConversations />
      </ErrorBoundary>

      <div className="px-2 py-3 border-t border-stone-200">
        <UserMenu />
      </div>
    </div>
  )
}

function SidebarConversations() {
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const lastSessionId = useSidebarStore((state) => state.lastSessionId)
  const setLastSessionId = useSidebarStore((state) => state.setLastSessionId)

  const [offset, setOffset] = useState(0)
  const limit = 30

  const { data, isLoading, error } = useConversations(offset, limit)
  const deleteConversation = useDeleteConversation()

  // Clear stale lastSessionId if it's not in the loaded conversation list
  useEffect(() => {
    if (lastSessionId && data?.conversations) {
      const exists = data.conversations.some((c) => c.session_id === lastSessionId)
      if (!exists) setLastSessionId(null)
    }
  }, [data?.conversations, lastSessionId, setLastSessionId])

  const handleNavigate = (id: string) => {
    navigate(`/chat/${id}`)
  }

  const handleDelete = (id: string) => {
    deleteConversation.mutate(id, {
      onSuccess: () => {
        if (id === lastSessionId) {
          setLastSessionId(null)
        }
        if (id === sessionId) {
          navigate('/chat')
        }
      },
    })
  }

  const hasMore = data ? offset + limit < data.total : false
  const hasPrev = offset > 0

  return (
    <>
      <div className="flex-1 overflow-y-auto px-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="px-3 py-8 text-center">
            <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
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
            <h2 className="text-xs text-stone-600 px-3 pt-4 pb-2">
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
    </>
  )
}

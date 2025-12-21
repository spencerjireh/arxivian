// Chat page - active chat with message history

import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ChevronLeft, Plus, Loader2 } from 'lucide-react'
import { useConversation } from '../api/conversations'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chatStore'
import ChatMessages from '../components/chat/ChatMessages'
import ChatInput from '../components/chat/ChatInput'

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const isNewChat = sessionId === 'new'

  // Use null for new chats, actual sessionId for existing ones
  const effectiveSessionId = isNewChat ? null : sessionId ?? null

  // Subscribe to streaming state directly from store for real-time updates
  const isStreaming = useChatStore((state) => state.isStreaming)
  const error = useChatStore((state) => state.error)

  const {
    messages,
    sendMessage,
    cancelStream,
    loadFromHistory,
    clearMessages,
  } = useChat(effectiveSessionId)

  // Fetch conversation history for existing sessions
  const { data: conversation, isLoading } = useConversation(
    isNewChat ? undefined : sessionId
  )

  // Load history when conversation data arrives
  useEffect(() => {
    if (conversation?.turns && conversation.turns.length > 0) {
      loadFromHistory(conversation.turns)
    }
  }, [conversation, loadFromHistory])

  // Clear messages when navigating to new chat
  useEffect(() => {
    if (isNewChat) {
      clearMessages()
    }
  }, [isNewChat, clearMessages])

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-medium text-gray-900">
              {isNewChat ? 'New Chat' : 'Conversation'}
            </h1>
            {!isNewChat && sessionId && (
              <p className="text-xs text-gray-500 font-mono">
                {sessionId.slice(0, 8)}...
              </p>
            )}
          </div>
        </div>

        <Link
          to="/new"
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          title="New chat"
        >
          <Plus className="w-5 h-5" />
        </Link>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Messages */}
      {!isLoading && <ChatMessages messages={messages} />}

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        onCancel={cancelStream}
      />
    </div>
  )
}

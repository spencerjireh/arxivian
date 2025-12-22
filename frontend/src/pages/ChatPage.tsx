// Chat page - active chat with message history

import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Loader2, AlertCircle } from 'lucide-react'
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

  // Load history when conversation data arrives, but only if messages cache is empty
  // This prevents overwriting messages that were just set during navigation from a new chat
  useEffect(() => {
    if (conversation?.turns && conversation.turns.length > 0 && messages.length === 0) {
      loadFromHistory(conversation.turns)
    }
  }, [conversation, loadFromHistory, messages.length])

  // Clear messages when navigating to new chat
  useEffect(() => {
    if (isNewChat) {
      clearMessages()
    }
  }, [isNewChat, clearMessages])

  return (
    <div className="flex flex-col h-screen">
      {/* Loading state */}
      {isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-6 h-6 animate-spin text-stone-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-sm text-stone-400">Loading conversation...</p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mx-6 mt-6 p-4 bg-red-50 border border-red-100 rounded-xl animate-fade-in">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" strokeWidth={1.5} />
            <div>
              <p className="text-sm font-medium text-red-800">Something went wrong</p>
              <p className="text-sm text-red-600 mt-0.5">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Messages - show immediately if we have messages (from cache), otherwise wait for loading */}
      {(!isLoading || messages.length > 0) && <ChatMessages messages={messages} />}

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        onCancel={cancelStream}
      />
    </div>
  )
}

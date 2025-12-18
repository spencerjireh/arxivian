// Chat page - active chat with message history

import { useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useConversation } from '../api/conversations'
import { useChatStore } from '../stores/chatStore'
import { useStreamChat } from '../hooks/useStreamChat'
import ChatMessages from '../components/chat/ChatMessages'
import ChatInput from '../components/chat/ChatInput'
import StreamStatus from '../components/chat/StreamStatus'

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const isNewChat = sessionId === 'new'

  const { setSessionId, loadHistory, reset, sessionId: storeSessionId, error } = useChatStore()
  const { sendMessage, cancelStream, isStreaming } = useStreamChat()

  // Fetch conversation history for existing sessions
  const { data: conversation, isLoading } = useConversation(
    isNewChat ? undefined : sessionId
  )

  // Initialize session ID from URL
  useEffect(() => {
    if (isNewChat) {
      reset()
    } else if (sessionId) {
      setSessionId(sessionId)
    }
  }, [sessionId, isNewChat, setSessionId, reset])

  // Load history when conversation data arrives
  useEffect(() => {
    if (conversation?.turns) {
      loadHistory(conversation.turns)
    }
  }, [conversation, loadHistory])

  // Update URL when new session is created
  useEffect(() => {
    if (isNewChat && storeSessionId && storeSessionId !== sessionId) {
      navigate(`/ask/${storeSessionId}`, { replace: true })
    }
  }, [isNewChat, storeSessionId, sessionId, navigate])

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <Link
            to="/ask"
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
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
          to="/ask/new"
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          title="New chat"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </Link>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex-1 flex items-center justify-center">
          <svg className="w-8 h-8 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
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
      )}

      {/* Error state */}
      {error && (
        <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Messages */}
      {!isLoading && <ChatMessages />}

      {/* Status indicator */}
      <StreamStatus />

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        onCancel={cancelStream}
      />
    </div>
  )
}

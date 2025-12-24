// Chat page - active chat with message history

import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useConversation } from '../api/conversations'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chatStore'
import ChatMessages from '../components/chat/ChatMessages'
import ChatInput from '../components/chat/ChatInput'
import EmptyConversationState from '../components/chat/EmptyConversationState'
import { fadeIn, transitions } from '../lib/animations'

export default function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const shouldReduceMotion = useReducedMotion()
  const isNewChat = !sessionId

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
  const { data: conversation } = useConversation(
    isNewChat ? undefined : sessionId
  )

  // Load history when conversation data arrives, but ONLY if:
  // 1. Messages cache is empty (we haven't loaded or received messages yet)
  // 2. This is the first time we're seeing this conversation data
  // NOTE: We must NOT include messages.length in dependencies to avoid
  // overwriting local messages when user sends new messages
  useEffect(() => {
    if (!conversation?.turns || conversation.turns.length === 0) {
      return
    }

    // Only load if cache is truly empty (page refresh, direct link)
    // Don't load if we already have messages (from streaming/navigation)
    if (messages.length === 0) {
      loadFromHistory(conversation.turns)
    }
    // Note: We don't merge/reload if we already have messages to avoid
    // overwriting local messages that haven't been persisted yet
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation?.turns, loadFromHistory])

  // Clear messages when navigating to new chat
  useEffect(() => {
    if (isNewChat) {
      clearMessages()
    }
  }, [isNewChat, clearMessages])

  const isEmpty = messages.length === 0
  const motionProps = shouldReduceMotion
    ? {}
    : { variants: fadeIn, initial: 'initial', animate: 'animate', exit: 'exit', transition: transitions.base }

  return (
    <div className="flex flex-col h-screen">
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

      <AnimatePresence mode="wait">
        {isEmpty ? (
          <motion.div key="empty" className="flex-1 flex flex-col" {...motionProps}>
            <EmptyConversationState
              onSend={sendMessage}
              isStreaming={isStreaming}
              onCancel={cancelStream}
            />
          </motion.div>
        ) : (
          <motion.div key="active" className="flex-1 flex flex-col min-h-0" {...motionProps}>
            <ChatMessages messages={messages} />
            <ChatInput
              onSend={sendMessage}
              isStreaming={isStreaming}
              onCancel={cancelStream}
              variant="bottom"
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

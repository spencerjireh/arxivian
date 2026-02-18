// Chat page - active chat with message history

import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useConversation } from '../api/conversations'
import { useChat } from '../hooks/useChat'
import { useChatStore } from '../stores/chatStore'
import { useSidebarStore } from '../stores/sidebarStore'
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

  const setLastSessionId = useSidebarStore((state) => state.setLastSessionId)

  // Subscribe to streaming state directly from store for real-time updates
  const isStreaming = useChatStore((state) => state.isStreaming)
  const error = useChatStore((state) => state.error)
  const setError = useChatStore((state) => state.setError)

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

  // Remember last-viewed conversation so "Chat" nav can return to it
  useEffect(() => {
    if (sessionId) {
      setLastSessionId(sessionId)
    }
  }, [sessionId, setLastSessionId])

  // Show error as toast and clear store error
  useEffect(() => {
    if (error) {
      toast.error('Something went wrong', { description: error })
      setError(null)
    }
  }, [error, setError])

  const isEmpty = messages.length === 0
  const motionProps = shouldReduceMotion
    ? {}
    : { variants: fadeIn, initial: 'initial', animate: 'animate', exit: 'exit', transition: transitions.base }

  return (
    <div className="flex flex-col h-screen">
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
          <motion.div key="active" className="flex-1 flex flex-col min-h-0 relative" {...motionProps}>
            <ChatMessages messages={messages} />
            <div className="absolute bottom-0 left-0 right-0">
              <ChatInput
                onSend={sendMessage}
                isStreaming={isStreaming}
                onCancel={cancelStream}
                variant="bottom"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

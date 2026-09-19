import { useEffect } from 'react'
import { MessageSquare, Plus } from 'lucide-react'
import { useConversation, usePaperConversations } from '../../api/conversations'
import { useChat } from '../../hooks/useChat'
import { useChatStore } from '../../stores/chatStore'
import { SCOPED_PROMPTS } from '../../lib/scopedPrompts'
import { selectClass } from '../../lib/formClasses'
import ChatInput from '../chat/ChatInput'
import ChatMessages from '../chat/ChatMessages'
import SuggestionChips from '../chat/SuggestionChips'
import Button from '../ui/Button'

interface ScopedChatPanelProps {
  arxivId: string
  paperTitle: string
  sessionId: string | null
  onSessionChange: (sessionId: string | null) => void
}

/**
 * Chat narrowed to one paper. Reuses the streaming + citation UI; the backend hides the
 * corpus-level tools and keeps retrieval inside the paper. One chat surface is mounted at
 * a time, so the stream is aborted on unmount.
 */
export default function ScopedChatPanel({ arxivId, paperTitle, sessionId, onSessionChange }: ScopedChatPanelProps) {
  const { messages, sendMessage, cancelStream, retryMessage, loadFromHistory, clearMessages } = useChat(
    sessionId,
    { arxivId, onSessionCreated: onSessionChange },
  )
  const isStreaming = useChatStore((s) => s.isStreaming)
  const { data: threads } = usePaperConversations(arxivId)
  const { data: conversation } = useConversation(sessionId ?? undefined)

  useEffect(() => {
    if (!conversation?.turns?.length) return
    if (messages.length === 0) loadFromHistory(conversation.turns)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation?.turns, loadFromHistory])

  useEffect(() => () => cancelStream(), [cancelStream])

  const startNewThread = () => {
    cancelStream()
    clearMessages()
    onSessionChange(null)
  }

  return (
    <section
      aria-label="Ask about this paper"
      className="bg-white border border-stone-200 rounded-xl flex flex-col h-[32rem] lg:h-[calc(100vh-8rem)] lg:sticky lg:top-6"
    >
      <header className="flex items-center gap-2 px-4 py-3 border-b border-stone-100">
        <MessageSquare className="w-4 h-4 text-stone-400" strokeWidth={1.5} />
        <h2 className="font-display text-lg text-stone-900 flex-1 truncate" title={paperTitle}>
          Ask about this paper
        </h2>
        {threads && threads.conversations.length > 0 && (
          <select
            aria-label="Thread"
            value={sessionId ?? ''}
            onChange={(e) => onSessionChange(e.target.value || null)}
            className={`${selectClass} max-w-40 text-xs py-1`}
          >
            <option value="">New thread</option>
            {threads.conversations.map((c) => (
              <option key={c.session_id} value={c.session_id}>
                {c.title ?? c.last_query ?? c.session_id}
              </option>
            ))}
          </select>
        )}
        {sessionId && (
          <Button variant="ghost" size="sm" onClick={startNewThread} leftIcon={<Plus className="w-4 h-4" strokeWidth={1.5} />}>
            New
          </Button>
        )}
      </header>

      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center px-4 gap-4">
          <p className="text-sm text-stone-500 text-center">
            Answers cite only this paper. Start with a seeded prompt or ask your own.
          </p>
          <SuggestionChips suggestions={SCOPED_PROMPTS} columns={1} onSelect={sendMessage} />
        </div>
      ) : (
        <ChatMessages messages={messages} onRetry={retryMessage} compact />
      )}

      <div className="px-3 pb-3 pt-2 border-t border-stone-100">
        <ChatInput onSend={sendMessage} isStreaming={isStreaming} onCancel={cancelStream} variant="centered" />
      </div>
    </section>
  )
}

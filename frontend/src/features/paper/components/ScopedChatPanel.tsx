// The only chat surface: a thread scoped to one paper (useChat + ?session= selection).
import { useEffect } from 'react'
import { MessageSquare, Plus } from 'lucide-react'
import { useChatStore } from '@/stores/chatStore'
import { selectClass } from '@/lib/formClasses'
import Button from '@/components/ui/Button'
import { useConversation, usePaperConversations } from '../api/get-conversation'
import { useChat } from '../hooks/useChat'
import { SCOPED_PROMPTS } from '../lib/scopedPrompts'
import ChatInput from './chat/ChatInput'
import ChatMessages from './chat/ChatMessages'
import SuggestionChips from './chat/SuggestionChips'

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
export default function ScopedChatPanel({
  arxivId,
  paperTitle,
  sessionId,
  onSessionChange,
}: ScopedChatPanelProps) {
  const { messages, sendMessage, cancelStream, retryMessage, loadFromHistory, clearMessages } =
    useChat(sessionId, { arxivId, onSessionCreated: onSessionChange })
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
      className="flex h-[32rem] flex-col rounded-xl border border-stone-200 bg-white lg:sticky lg:top-20 lg:h-[calc(100vh-7rem)]"
    >
      <header className="flex items-center gap-2 border-b border-stone-100 px-4 py-3">
        <MessageSquare className="h-4 w-4 text-stone-400" strokeWidth={1.5} />
        <h2 className="font-display flex-1 truncate text-lg text-stone-900" title={paperTitle}>
          Ask about this paper
        </h2>
        {threads && threads.conversations.length > 0 && (
          <select
            aria-label="Thread"
            value={sessionId ?? ''}
            onChange={(e) => onSessionChange(e.target.value || null)}
            className={`${selectClass} max-w-40 py-1 text-xs`}
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
          <Button
            variant="ghost"
            size="sm"
            onClick={startNewThread}
            leftIcon={<Plus className="h-4 w-4" strokeWidth={1.5} />}
          >
            New
          </Button>
        )}
      </header>

      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4">
          <p className="text-center text-sm text-stone-500">
            Answers cite only this paper. Start with a seeded prompt or ask your own.
          </p>
          <SuggestionChips suggestions={SCOPED_PROMPTS} columns={1} onSelect={sendMessage} />
        </div>
      ) : (
        <ChatMessages messages={messages} onRetry={retryMessage} compact />
      )}

      <div className="border-t border-stone-100 px-3 pt-2 pb-3">
        <ChatInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          onCancel={cancelStream}
          variant="centered"
        />
      </div>
    </section>
  )
}

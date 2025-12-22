// User/assistant message bubble component

import { User, Sparkles } from 'lucide-react'
import type { Message, ThinkingStep } from '../../types/api'
import SourceCard from './SourceCard'
import MetadataPanel from './MetadataPanel'
import MarkdownRenderer from './MarkdownRenderer'
import ThinkingTimeline from './ThinkingTimeline'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  streamingContent?: string
  streamingThinkingSteps?: ThinkingStep[]
  isFirst?: boolean
}

export default function ChatMessage({
  message,
  isStreaming,
  streamingContent,
  streamingThinkingSteps,
  isFirst,
}: ChatMessageProps) {
  const isUser = message.role === 'user'
  const content = isStreaming ? streamingContent : message.content

  // Use streaming thinking steps if streaming, otherwise use persisted ones from message
  const thinkingSteps = isStreaming
    ? (streamingThinkingSteps ?? [])
    : message.thinkingSteps

  return (
    <div className={`animate-fade-in ${isFirst ? '' : ''} ${isUser ? 'flex justify-end' : ''}`}>
      <div className={isUser ? 'max-w-[80%]' : ''}>
        {/* Message header with role indicator */}
        <div className={`flex items-center gap-2.5 mb-3 ${isUser ? 'justify-end' : ''}`}>
          {isUser ? (
            <>
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-100">
                <User className="w-3.5 h-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </>
          ) : (
            <>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-900">
                <Sparkles className="w-3.5 h-3.5 text-white" strokeWidth={1.5} />
              </div>
              <span className="text-sm font-medium text-stone-500">Agent</span>
            </>
          )}
        </div>

        {/* Message content */}
        <div className={isUser ? 'pr-9 text-right' : 'pl-9'}>
          {/* Thinking timeline - only for assistant messages */}
          {!isUser && thinkingSteps && thinkingSteps.length > 0 && (
            <div className="mb-4">
              <ThinkingTimeline steps={thinkingSteps} isStreaming={isStreaming} />
            </div>
          )}

          {/* Message text */}
          <div className="text-stone-800">
            {isUser ? (
              <div className="whitespace-pre-wrap leading-relaxed">{content}</div>
            ) : (
              <div className="prose-stone">
                <MarkdownRenderer content={content || ''} />
                {isStreaming && (
                  <span className="inline-block w-0.5 h-5 ml-0.5 bg-stone-400 cursor-blink align-text-bottom" />
                )}
              </div>
            )}
          </div>

          {/* Sources - only for assistant messages */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-6 pt-6 border-t border-stone-100">
              <h4 className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">
                Sources
              </h4>
              <div className="space-y-2">
                {message.sources.map((source) => (
                  <SourceCard key={source.arxiv_id} source={source} />
                ))}
              </div>
            </div>
          )}

          {/* Metadata - only for assistant messages */}
          {!isUser && message.metadata && (
            <div className="mt-4 pt-4 border-t border-stone-100">
              <MetadataPanel metadata={message.metadata} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

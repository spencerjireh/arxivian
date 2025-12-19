// User/assistant message bubble component

import type { Message, ThinkingStep } from '../../types/api'
import SourceCard from './SourceCard'
import MetadataPanel from './MetadataPanel'
import MarkdownRenderer from './MarkdownRenderer'
import ThinkingPanel from './ThinkingPanel'

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
  streamingContent?: string
  streamingThinkingSteps?: ThinkingStep[]
}

export default function ChatMessage({
  message,
  isStreaming,
  streamingContent,
  streamingThinkingSteps,
}: ChatMessageProps) {
  const isUser = message.role === 'user'
  const content = isStreaming ? streamingContent : message.content

  // Use streaming thinking steps if streaming, otherwise use persisted ones from message
  // Ensure we always have an array (not undefined) for proper rendering
  const thinkingSteps = isStreaming
    ? (streamingThinkingSteps ?? [])
    : message.thinkingSteps

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] ${
          isUser
            ? 'bg-gray-100 rounded-2xl rounded-br-md'
            : 'bg-white border border-gray-200 rounded-2xl rounded-bl-md'
        } px-4 py-3`}
      >
        {/* Thinking panel - only for assistant messages */}
        {!isUser && thinkingSteps && thinkingSteps.length > 0 && (
          <ThinkingPanel steps={thinkingSteps} isStreaming={isStreaming} />
        )}

        {/* Message content */}
        <div className="text-gray-800 break-words">
          {isUser ? (
            // User messages: render as plain text with whitespace preserved
            <div className="whitespace-pre-wrap">{content}</div>
          ) : (
            // Assistant messages: render as markdown
            <>
              <MarkdownRenderer content={content || ''} />
              {isStreaming && (
                <span className="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse" />
              )}
            </>
          )}
        </div>

        {/* Sources - only for assistant messages */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-500 mb-2">Sources</p>
            <div className="space-y-2">
              {message.sources.map((source) => (
                <SourceCard key={source.arxiv_id} source={source} />
              ))}
            </div>
          </div>
        )}

        {/* Metadata - only for assistant messages */}
        {!isUser && message.metadata && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <MetadataPanel metadata={message.metadata} />
          </div>
        )}
      </div>
    </div>
  )
}

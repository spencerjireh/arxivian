import { useState } from 'react'
import logoIcon from '../../assets/logo-icon.png'
import ChatInput from './ChatInput'
import SuggestionChips from './SuggestionChips'

interface EmptyConversationStateProps {
  onSend: (query: string) => void
  isStreaming: boolean
  onCancel?: () => void
}

export default function EmptyConversationState({
  onSend,
  isStreaming,
  onCancel,
}: EmptyConversationStateProps) {
  const [selectedPrompt, setSelectedPrompt] = useState<string>()

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
      <div className="w-full max-w-2xl flex flex-col items-center">
        {/* Icon */}
        <div
          style={{ '--stagger-index': 0 } as React.CSSProperties}
          className="w-14 h-14 rounded-2xl bg-stone-100 border border-stone-200 flex items-center justify-center mb-6 animate-stagger"
        >
          <img src={logoIcon} alt="" className="w-7 h-7" aria-hidden="true" />
        </div>

        {/* Heading */}
        <h1
          style={{ '--stagger-index': 1 } as React.CSSProperties}
          className="font-display text-3xl sm:text-4xl text-stone-900 mb-3 tracking-tight text-center animate-stagger"
        >
          How can I help you today?
        </h1>

        {/* Subtitle */}
        <p
          style={{ '--stagger-index': 2 } as React.CSSProperties}
          className="text-stone-500 text-center mb-8 max-w-md leading-relaxed animate-stagger"
        >
          Ask questions about research papers, explore academic literature, or discover new insights.
        </p>

        {/* Centered Input */}
        <div
          style={{ '--stagger-index': 3 } as React.CSSProperties}
          className="w-full mb-8 animate-stagger"
        >
          <ChatInput
            onSend={onSend}
            isStreaming={isStreaming}
            onCancel={onCancel}
            variant="centered"
            defaultValue={selectedPrompt}
          />
        </div>

        {/* Suggestion Chips */}
        <SuggestionChips onSelect={setSelectedPrompt} />
      </div>
    </div>
  )
}

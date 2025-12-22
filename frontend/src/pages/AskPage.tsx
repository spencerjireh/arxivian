// Ask page - conversation list + new chat button

import { useNavigate } from 'react-router-dom'
import { Plus, ArrowRight } from 'lucide-react'
import ConversationList from '../components/conversations/ConversationList'

export default function AskPage() {
  const navigate = useNavigate()

  return (
    <div className="max-w-5xl mx-auto px-6 sm:px-8 py-12 animate-fade-in">
      {/* Header section */}
      <div className="mb-10">
        <h1 className="font-display text-3xl sm:text-4xl text-stone-900 mb-3 elegant-line pb-2">
          Conversations
        </h1>
        <p className="text-stone-500 text-base leading-relaxed max-w-md">
          Explore research papers through conversation.
          Ask questions and receive answers grounded in academic literature.
        </p>
      </div>

      {/* New chat button */}
      <button
        onClick={() => navigate('/new')}
        className="w-full mb-8 group"
      >
        <div className="flex items-center justify-between p-5 bg-white border border-stone-200 rounded-xl transition-all duration-200 hover:border-stone-300 hover:shadow-sm">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-lg bg-stone-900 flex items-center justify-center">
              <Plus className="w-5 h-5 text-white" strokeWidth={1.5} />
            </div>
            <div className="text-left">
              <span className="block text-stone-900 font-medium">Start new conversation</span>
              <span className="text-sm text-stone-400">Ask about research papers</span>
            </div>
          </div>
          <ArrowRight
            className="w-5 h-5 text-stone-300 transition-all duration-200 group-hover:text-stone-500 group-hover:translate-x-1"
            strokeWidth={1.5}
          />
        </div>
      </button>

      {/* Conversation list */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-stone-400 uppercase tracking-wider">
            Recent
          </h2>
        </div>
        <div className="bg-white border border-stone-200 rounded-xl overflow-hidden">
          <ConversationList />
        </div>
      </div>
    </div>
  )
}

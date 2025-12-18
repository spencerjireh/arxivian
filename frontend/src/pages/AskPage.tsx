// Ask page - conversation list + new chat button

import { useNavigate } from 'react-router-dom'
import ConversationList from '../components/conversations/ConversationList'

export default function AskPage() {
  const navigate = useNavigate()

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Conversations</h1>
          <p className="text-sm text-gray-500 mt-1">
            Ask questions about research papers
          </p>
        </div>
        <button
          onClick={() => navigate('/ask/new')}
          className="inline-flex items-center px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg
            className="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <ConversationList />
      </div>
    </div>
  )
}

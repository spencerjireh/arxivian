// Workflow step indicator component

import { useChatStore } from '../../stores/chatStore'

export default function StreamStatus() {
  const { currentStatus, isStreaming } = useChatStore()

  if (!isStreaming || !currentStatus) {
    return null
  }

  return (
    <div className="px-4 py-2 transition-all duration-200">
      <div className="inline-flex items-center px-3 py-1.5 bg-gray-100 rounded-full text-sm text-gray-600">
        <svg
          className="w-4 h-4 mr-2 animate-spin"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
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
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        {currentStatus}
      </div>
    </div>
  )
}

// Expandable source citation component

import { useState } from 'react'
import type { SourceInfo } from '../../types/api'

interface SourceCardProps {
  source: SourceInfo
}

export default function SourceCard({ source }: SourceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-100 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 text-left flex items-center justify-between hover:bg-gray-100 transition-colors duration-200"
      >
        <div className="flex-1 min-w-0">
          <span className="text-xs font-mono text-gray-500">{source.arxiv_id}</span>
          <p className="text-sm text-gray-700 truncate">{source.title}</p>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 flex-shrink-0 ml-2 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-3 py-2 border-t border-gray-100 space-y-2 transition-all duration-200">
          <div>
            <span className="text-xs text-gray-500">Authors</span>
            <p className="text-sm text-gray-700">{source.authors.join(', ')}</p>
          </div>

          {source.published_date && (
            <div>
              <span className="text-xs text-gray-500">Published</span>
              <p className="text-sm text-gray-700">{source.published_date}</p>
            </div>
          )}

          <div>
            <span className="text-xs text-gray-500">Relevance Score</span>
            <p className="text-sm text-gray-700">
              {(source.relevance_score * 100).toFixed(1)}%
              {source.was_graded_relevant !== undefined && (
                <span
                  className={`ml-2 text-xs ${
                    source.was_graded_relevant ? 'text-green-600' : 'text-amber-600'
                  }`}
                >
                  {source.was_graded_relevant ? 'Graded relevant' : 'Graded not relevant'}
                </span>
              )}
            </p>
          </div>

          <a
            href={source.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            View PDF
            <svg
              className="w-3 h-3 ml-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>
      )}
    </div>
  )
}

// Expandable execution metadata component

import { useState } from 'react'
import type { MetadataEventData } from '../../types/api'

interface MetadataPanelProps {
  metadata: MetadataEventData
}

export default function MetadataPanel({ metadata }: MetadataPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="text-xs text-gray-500 hover:text-gray-700 flex items-center transition-colors duration-200"
      >
        {isExpanded ? 'Hide details' : 'View details'}
        <svg
          className={`w-3 h-3 ml-1 transition-transform duration-200 ${
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
        <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs space-y-2 transition-all duration-200">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="text-gray-500">Provider</span>
              <p className="text-gray-700 font-medium">{metadata.provider}</p>
            </div>
            <div>
              <span className="text-gray-500">Model</span>
              <p className="text-gray-700 font-medium">{metadata.model}</p>
            </div>
            <div>
              <span className="text-gray-500">Execution Time</span>
              <p className="text-gray-700 font-medium">
                {(metadata.execution_time_ms / 1000).toFixed(2)}s
              </p>
            </div>
            <div>
              <span className="text-gray-500">Retrieval Attempts</span>
              <p className="text-gray-700 font-medium">{metadata.retrieval_attempts}</p>
            </div>
          </div>

          {metadata.guardrail_score !== undefined && (
            <div>
              <span className="text-gray-500">Guardrail Score</span>
              <p className="text-gray-700 font-medium">{metadata.guardrail_score}%</p>
            </div>
          )}

          {metadata.rewritten_query && (
            <div>
              <span className="text-gray-500">Rewritten Query</span>
              <p className="text-gray-700">{metadata.rewritten_query}</p>
            </div>
          )}

          {metadata.reasoning_steps.length > 0 && (
            <div>
              <span className="text-gray-500">Reasoning Steps</span>
              <ol className="mt-1 list-decimal list-inside text-gray-700 space-y-0.5">
                {metadata.reasoning_steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            </div>
          )}

          {metadata.session_id && (
            <div>
              <span className="text-gray-500">Session</span>
              <p className="text-gray-700 font-mono text-[10px]">{metadata.session_id}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { BookOpen, Search, Lightbulb, GitCompare } from 'lucide-react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

export interface Suggestion {
  icon: LucideIcon
  title: string
  prompt: string
}

interface SuggestionChipsProps {
  onSelect: (prompt: string) => void
  suggestions?: Suggestion[]
  columns?: 1 | 2
}

const SUGGESTIONS: Suggestion[] = [
  {
    icon: BookOpen,
    title: 'Summarize a paper',
    prompt: 'Can you summarize the key findings and methodology of this research paper?',
  },
  {
    icon: Search,
    title: 'Find research',
    prompt: 'Find recent research papers about',
  },
  {
    icon: Lightbulb,
    title: 'Explain a concept',
    prompt: 'Explain the concept of',
  },
  {
    icon: GitCompare,
    title: 'Compare approaches',
    prompt: 'Compare the different approaches to',
  },
]

export default function SuggestionChips({
  onSelect,
  suggestions = SUGGESTIONS,
  columns = 2,
}: SuggestionChipsProps) {
  return (
    <div
      className={clsx(
        'grid w-full max-w-xl gap-3',
        columns === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'
      )}
    >
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          style={{ '--stagger-index': index } as React.CSSProperties}
          onClick={() => onSelect(suggestion.prompt)}
          className="group animate-stagger hover-lift relative flex items-center gap-2.5 rounded-lg border border-stone-100 bg-stone-50/80 px-3.5 py-2.5 text-left transition-all duration-200 hover:border-stone-200 hover:bg-stone-100/80"
        >
          <suggestion.icon
            className="h-4 w-4 flex-shrink-0 text-stone-400 transition-colors duration-200 group-hover:text-amber-700"
            strokeWidth={1.5}
          />
          <span className="text-sm font-medium text-stone-600 transition-colors duration-200 group-hover:text-stone-800">
            {suggestion.title}
          </span>
        </button>
      ))}
    </div>
  )
}

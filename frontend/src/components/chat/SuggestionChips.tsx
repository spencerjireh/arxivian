import { motion, useReducedMotion } from 'framer-motion'
import { BookOpen, Search, Lightbulb, GitCompare } from 'lucide-react'
import { transitions } from '../../lib/animations'

interface SuggestionChipsProps {
  onSelect: (prompt: string) => void
}

const SUGGESTIONS = [
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

export default function SuggestionChips({ onSelect }: SuggestionChipsProps) {
  const shouldReduceMotion = useReducedMotion()

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
      {SUGGESTIONS.map((suggestion, index) => (
        <motion.button
          key={index}
          initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            ...transitions.base,
            delay: shouldReduceMotion ? 0 : 0.05 * index,
          }}
          whileHover={shouldReduceMotion ? undefined : { y: -2 }}
          whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
          onClick={() => onSelect(suggestion.prompt)}
          className="group relative flex items-center gap-2.5 px-3.5 py-2.5 text-left bg-stone-50/80 border border-stone-100 rounded-lg hover:bg-stone-100/80 hover:border-stone-200 transition-all duration-200 opacity-0"
        >
          <suggestion.icon
            className="w-4 h-4 text-stone-400 group-hover:text-amber-700 transition-colors duration-200 flex-shrink-0"
            strokeWidth={1.5}
          />
          <span className="text-sm text-stone-600 font-medium group-hover:text-stone-800 transition-colors duration-200">
            {suggestion.title}
          </span>
        </motion.button>
      ))}
    </div>
  )
}

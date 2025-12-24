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
          className="group relative flex items-start gap-3 p-4 text-left bg-white/60 backdrop-blur-sm border border-stone-200/80 rounded-xl hover:bg-white hover:border-stone-300 hover:shadow-sm transition-colors duration-200 opacity-0"
        >
          <div className="w-9 h-9 rounded-lg bg-stone-100 flex items-center justify-center flex-shrink-0 group-hover:bg-stone-200/80 transition-colors duration-200">
            <suggestion.icon
              className="w-[18px] h-[18px] text-stone-500 group-hover:text-stone-700 transition-colors duration-200"
              strokeWidth={1.5}
            />
          </div>
          <span className="text-sm text-stone-600 font-medium leading-relaxed pt-1.5 group-hover:text-stone-800 transition-colors duration-200">
            {suggestion.title}
          </span>
        </motion.button>
      ))}
    </div>
  )
}

// Landing feature grid: the four product features, each with an icon, copy and illustration.
import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles, BookOpen, Search, GitBranch } from 'lucide-react'
import clsx from 'clsx'
import { staggerContainer, staggerItem, transitions } from '../../lib/animations'
import {
  CitationExplorerIllustration,
  PaperLibraryIllustration,
  ResearchAssistantIllustration,
  SmartSearchIllustration,
} from './FeatureIllustrations'

const features = [
  {
    icon: Sparkles,
    title: 'Research Assistant',
    description:
      'Ask questions about papers and receive grounded answers with citations drawn directly from the literature.',
    size: 'large' as const,
    illustration: ResearchAssistantIllustration,
  },
  {
    icon: BookOpen,
    title: 'Paper Library',
    description:
      'Build a personal collection of arXiv papers, automatically processed and indexed for semantic retrieval.',
    size: 'small' as const,
    illustration: PaperLibraryIllustration,
  },
  {
    icon: Search,
    title: 'Smart Search',
    description:
      'Answers are powered by hybrid retrieval -- vector similarity and full-text matching work together to find the most relevant passages.',
    size: 'small' as const,
    illustration: SmartSearchIllustration,
  },
  {
    icon: GitBranch,
    title: 'Citation Explorer',
    description:
      'Trace the lineage of ideas by exploring citation graphs -- see what a paper builds on and what builds on it.',
    size: 'small' as const,
    illustration: CitationExplorerIllustration,
  },
]

export default function FeatureGrid() {
  const shouldReduceMotion = useReducedMotion()

  return (
    <section className="dot-grid relative z-10 px-4 pt-16 pb-24 sm:px-6 sm:pt-20 sm:pb-32 lg:px-8">
      <motion.div
        className="mx-auto max-w-6xl"
        variants={staggerContainer}
        initial="initial"
        whileInView="animate"
        viewport={{ once: true, margin: '-80px' }}
      >
        <motion.h2
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="font-display mb-12 text-center text-2xl tracking-tight text-stone-900 sm:text-3xl"
        >
          Built for serious research
        </motion.h2>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, description, size, illustration: Illustration }) => (
            <motion.div
              key={title}
              variants={shouldReduceMotion ? undefined : staggerItem}
              transition={transitions.base}
              whileHover={shouldReduceMotion ? undefined : { y: -4, transition: { duration: 0.2 } }}
              className={clsx(
                'flex flex-col rounded-xl border border-stone-200 bg-white p-6 transition-colors duration-200 hover:border-stone-300',
                size === 'large' && 'md:col-span-2 lg:col-span-2'
              )}
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100">
                <Icon className="h-5 w-5 text-stone-700" strokeWidth={1.5} />
              </div>
              <h3 className="font-display mb-2 text-lg font-semibold text-stone-900">{title}</h3>
              <p className="mb-4 text-sm leading-relaxed text-stone-500">{description}</p>
              <div className="mt-auto">
                <Illustration />
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}

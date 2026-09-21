// Landing feature grid: the four product features, each with an icon, copy and illustration.
import { motion, useReducedMotion } from 'framer-motion'
import { Bookmark, CalendarDays, MessageSquare, Quote } from 'lucide-react'
import clsx from 'clsx'
import { staggerContainer, staggerItem, transitions } from '../../lib/animations'
import {
  EvidenceIllustration,
  LifecycleIllustration,
  ScopedChatIllustration,
  WeeklyDigestIllustration,
} from './FeatureIllustrations'

const features = [
  {
    icon: CalendarDays,
    title: 'Weekly digest',
    description:
      'New submissions in your arXiv categories are triaged and scored once a week. Cards rank by a composite of four dimensions and by fit with your compute profile: laptop, single GPU or cloud.',
    size: 'large' as const,
    illustration: WeeklyDigestIllustration,
  },
  {
    icon: Quote,
    title: 'Evidence behind every score',
    description:
      'Each dimension stores the passages it was judged on. Open a paper to see the level distribution, every atomic judgment and its quoted evidence.',
    size: 'small' as const,
    illustration: EvidenceIllustration,
  },
  {
    icon: Bookmark,
    title: 'Save, dismiss, implement',
    description:
      'Triage from the cards alone. Saved and in-progress papers live in your library; dismissals are one click.',
    size: 'small' as const,
    illustration: LifecycleIllustration,
  },
  {
    icon: MessageSquare,
    title: 'Chat scoped to one paper',
    description:
      "Ask about the core method, a minimal repo layout or the risky parts of a reproduction. Answers retrieve from that paper's full text only.",
    size: 'small' as const,
    illustration: ScopedChatIllustration,
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
          What a card tells you
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

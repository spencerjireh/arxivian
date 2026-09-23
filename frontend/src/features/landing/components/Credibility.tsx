// Landing "how it works" section (#credibility): the four dimensions and a sample breakdown.
import { motion, useReducedMotion } from 'framer-motion'
import { staggerContainer, staggerItem, transitions } from '@/lib/animations'
import SectionDivider from './SectionDivider'

const ROWS = [
  {
    dimension: 'Method clarity',
    level: 'Level 3 of 4',
    evidence: 'Algorithm 1 gives the full training loop; hyperparameters are listed in Table 4.',
  },
  {
    dimension: 'Resource feasibility',
    level: 'One consumer GPU',
    evidence: 'All experiments ran on a single RTX 4090 in under six hours.',
  },
  {
    dimension: 'Data availability',
    level: 'PASS',
    evidence: 'We evaluate on WikiText-103 and PG-19.',
  },
  {
    dimension: 'Demand',
    level: 'Rising',
    evidence: '41 citations in 3 months (Semantic Scholar).',
  },
]

export default function Credibility() {
  const shouldReduceMotion = useReducedMotion()

  return (
    <section
      id="credibility"
      className="relative z-10 bg-[#FAFAF9] px-4 pb-24 sm:px-6 sm:pb-32 lg:px-8"
    >
      <SectionDivider className="mb-16" />

      <motion.div
        className="mx-auto max-w-4xl text-center"
        variants={staggerContainer}
        initial="initial"
        whileInView="animate"
        viewport={{ once: true, margin: '-80px' }}
      >
        <motion.p
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="font-display mb-2 text-2xl tracking-tight text-stone-900 sm:text-3xl"
        >
          Four dimensions:{' '}
          <span className="text-stone-500">
            method clarity, resource feasibility, data availability, demand
          </span>
        </motion.p>

        <motion.p
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="mb-12 text-sm text-stone-400"
        >
          One paper, expanded
        </motion.p>

        {/* Sample score breakdown */}
        <motion.div
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="mx-auto max-w-2xl divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white text-left shadow-sm"
        >
          {ROWS.map((row) => (
            <div key={row.dimension} className="flex items-start gap-4 p-5">
              <div className="w-40 shrink-0">
                <p className="text-sm font-medium text-stone-900">{row.dimension}</p>
                <p className="mt-0.5 text-xs text-stone-500">{row.level}</p>
              </div>
              <blockquote className="flex-1 border-l-2 border-stone-200 pl-3 text-sm leading-relaxed text-stone-600">
                {row.evidence}
              </blockquote>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </section>
  )
}

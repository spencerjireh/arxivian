// Landing "how it works" section (#credibility): the catalog stat line and a sample exchange.
import { motion, useReducedMotion } from 'framer-motion'
import { User } from 'lucide-react'
import logoIcon from '../../assets/logo-icon.png'
import { staggerContainer, staggerItem, transitions } from '../../lib/animations'
import SectionDivider from './SectionDivider'

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
          Search and ingest from arXiv's <span className="text-stone-500">2,400,000+</span> paper
          catalog
        </motion.p>

        <motion.p
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="mb-12 text-sm text-stone-400"
        >
          See it in action
        </motion.p>

        {/* Sample Q&A card */}
        <motion.div
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.base}
          className="mx-auto max-w-2xl rounded-xl border border-stone-200 bg-white text-left shadow-sm"
        >
          {/* Question */}
          <div className="p-5">
            <div className="flex justify-end">
              <div className="max-w-[80%]">
                <div className="mb-2 flex items-center justify-end gap-2.5">
                  <span className="text-sm font-medium text-stone-500">You</span>
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                    <User className="h-3.5 w-3.5 text-stone-500" strokeWidth={1.5} />
                  </div>
                </div>
                <div className="pr-9 text-right text-sm leading-relaxed text-stone-800">
                  Summarize the key findings of arXiv:2301.07041
                </div>
              </div>
            </div>
          </div>

          <hr className="border-stone-100" />

          {/* Answer */}
          <div className="p-5">
            <div className="mb-2 flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                <img src={logoIcon} alt="" className="h-4 w-4" aria-hidden="true" />
              </div>
              <span className="text-sm font-medium text-stone-500">Arxivian</span>
            </div>
            <div className="space-y-2 pl-9 text-sm leading-relaxed text-stone-600">
              <p>
                The paper introduces{' '}
                <strong className="text-stone-800">Retrieval-Augmented Generation (RAG)</strong> as
                a framework for grounding language model outputs in retrieved evidence, reducing
                hallucination and improving factual accuracy across knowledge-intensive tasks.
              </p>
              <p>
                Key findings include a 15% improvement in factual consistency over baseline models,
                with the retrieval component enabling verifiable citations back to source documents.
              </p>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  )
}

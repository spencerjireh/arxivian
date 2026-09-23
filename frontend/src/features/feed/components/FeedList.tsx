// Feed: the card list; a dismissed card collapses out when the cache updater removes it.
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import FeedCard from './FeedCard'
import type { FeedItem } from '@/types/api'

interface FeedListProps {
  items: FeedItem[]
  signedIn: boolean
  /** Library lists offer Mark as Implementing / Mark as shipped; the feed does not. */
  offerImplementing?: boolean
}

/** Single column; each card owns its lifecycle actions. */
export default function FeedList({ items, signedIn, offerImplementing = false }: FeedListProps) {
  const reduceMotion = useReducedMotion()
  return (
    <div className="space-y-4">
      <AnimatePresence initial={false}>
        {items.map((item) => (
          <motion.div
            key={item.paper.arxiv_id}
            layout={!reduceMotion}
            initial={false}
            exit={reduceMotion ? undefined : { opacity: 0, height: 0, marginBottom: 0 }}
            transition={{ duration: 0.18 }}
          >
            <FeedCard item={item} signedIn={signedIn} offerImplementing={offerImplementing} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

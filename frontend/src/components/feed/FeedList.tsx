import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import FeedCard from './FeedCard'
import type { PendingAction } from './CardActions'
import type { FeedItem } from '../../types/api'

interface FeedListProps {
  items: FeedItem[]
  onSave: (arxivId: string) => void
  onDismiss: (arxivId: string) => void
  onImplementing: (arxivId: string) => void
  pendingFor: (arxivId: string) => PendingAction
}

/** Single column; a dismissed card collapses out (the cache updater removes it). */
export default function FeedList({ items, onSave, onDismiss, onImplementing, pendingFor }: FeedListProps) {
  const reduceMotion = useReducedMotion()
  return (
    <div className="max-w-3xl space-y-4">
      <AnimatePresence initial={false}>
        {items.map((item) => (
          <motion.div
            key={item.paper.arxiv_id}
            layout={!reduceMotion}
            initial={false}
            exit={reduceMotion ? undefined : { opacity: 0, height: 0, marginBottom: 0 }}
            transition={{ duration: 0.18 }}
          >
            <FeedCard
              item={item}
              onSave={onSave}
              onDismiss={onDismiss}
              onImplementing={onImplementing}
              pendingAction={pendingFor(item.paper.arxiv_id)}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

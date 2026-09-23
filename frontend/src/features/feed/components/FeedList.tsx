// Feed: the card list with loading, empty and error states.
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import FeedCard from './FeedCard'
import type { PendingAction } from '@/features/paper/components/CardActions'
import type { FeedItem } from '@/types/api'

interface FeedListProps {
  items: FeedItem[]
  signedIn: boolean
  onSave: (arxivId: string) => void
  onDismiss: (arxivId: string) => void
  onImplementing?: (arxivId: string) => void
  onShip?: (arxivId: string, repoUrl: string) => void
  pendingFor: (arxivId: string) => PendingAction
}

/** Single column; a dismissed card collapses out (the cache updater removes it). */
export default function FeedList({
  items,
  signedIn,
  onSave,
  onDismiss,
  onImplementing,
  onShip,
  pendingFor,
}: FeedListProps) {
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
            <FeedCard
              item={item}
              signedIn={signedIn}
              onSave={onSave}
              onDismiss={onDismiss}
              onImplementing={onImplementing}
              onShip={onShip}
              pendingAction={pendingFor(item.paper.arxiv_id)}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

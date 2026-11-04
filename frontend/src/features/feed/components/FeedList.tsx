// Feed and Library: the post list; a dismissed post collapses out when the cache updater removes it.
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import FeedPost from './FeedPost'
import type { FeedItem } from '@/types/api'

interface FeedListProps {
  items: FeedItem[]
  signedIn: boolean
  /** Library lists offer Mark as Implementing / Mark as shipped; the feed does not. */
  offerImplementing?: boolean
  /** Library opens every post; the feed starts collapsed. */
  defaultExpanded?: boolean
}

/**
 * Single column of posts separated by rule lines. The parent remounts the list (by key)
 * when the view changes, so the only exit that animates is a dismissal; `layout` is left
 * off because a few hundred siblings re-measuring on every removal is visible jank.
 */
export default function FeedList({
  items,
  signedIn,
  offerImplementing = false,
  defaultExpanded = false,
}: FeedListProps) {
  const reduceMotion = useReducedMotion()
  return (
    <div className="divide-y divide-stone-200 border-y border-stone-200">
      <AnimatePresence initial={false}>
        {items.map((item) => (
          <motion.div
            key={item.paper.arxiv_id}
            initial={false}
            exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <FeedPost
              item={item}
              signedIn={signedIn}
              offerImplementing={offerImplementing}
              defaultExpanded={defaultExpanded}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

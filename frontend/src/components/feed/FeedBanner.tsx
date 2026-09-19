import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Newspaper, X } from 'lucide-react'

const STORAGE_KEY = 'feed-banner-dismissed'

function readDismissed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

/** Entry point from the chat home to the feed (Phase 2 keeps chat as the default). */
export default function FeedBanner() {
  const [dismissed, setDismissed] = useState(readDismissed)
  if (dismissed) return null

  const dismiss = () => {
    setDismissed(true)
    try {
      localStorage.setItem(STORAGE_KEY, '1')
    } catch {
      // ignore
    }
  }

  return (
    <div
      className="w-full max-w-2xl mb-6 flex items-center gap-3 rounded-lg border border-amber-200 bg-[var(--color-accent-soft)] px-4 py-2.5 text-sm text-amber-900"
      role="status"
    >
      <Newspaper className="w-4 h-4 shrink-0" strokeWidth={1.5} />
      <span className="flex-1">
        Your weekly implementability feed is live.{' '}
        <Link to="/feed" className="font-medium underline underline-offset-2">
          Open the feed
        </Link>
      </span>
      <button
        type="button"
        onClick={dismiss}
        className="p-1 rounded hover:bg-amber-100"
        aria-label="Dismiss banner"
      >
        <X className="w-4 h-4" strokeWidth={1.5} />
      </button>
    </div>
  )
}

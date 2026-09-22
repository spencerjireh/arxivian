// /library route: the caller's papers grouped Saved / Implementing / Shipped (GET /users/me/library).
import { Link } from 'react-router-dom'
import { AlertCircle, BookOpen } from 'lucide-react'
import Chip from '@/components/ui/Chip'
import Spinner from '@/components/ui/Spinner'
import StatusBlock from '@/components/ui/StatusBlock'
import FeedList from '@/features/feed/components/FeedList'
import { useLibrary } from '@/features/paper/api/get-library'
import { getUserMessage } from '@/lib/errors'
import type { LibraryGroup, LibraryResponse } from '@/types/api'

const GROUPS: { key: LibraryGroup; label: string }[] = [
  { key: 'saved', label: 'Saved' },
  { key: 'implementing', label: 'Implementing' },
  { key: 'shipped', label: 'Shipped' },
]

const EMPTY: LibraryResponse = { saved: [], implementing: [], shipped: [] }

/** The return-visit surface: the caller's papers grouped saved -> implementing -> shipped. */
export default function LibraryPage() {
  const { data, isLoading, error } = useLibrary()
  const library = data ?? EMPTY
  const total = GROUPS.reduce((n, g) => n + library[g.key].length, 0)

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <div className="pb-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-semibold text-stone-900">Library</h1>
          {data && (
            <span className="font-mono text-sm text-stone-400">
              {total} paper{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      <div>
        {isLoading ? (
          <Spinner />
        ) : error ? (
          <StatusBlock icon={AlertCircle} tone="error" title={getUserMessage(error)} />
        ) : total === 0 ? (
          <StatusBlock icon={BookOpen} title="Nothing saved yet">
            <p className="mt-1 text-sm text-stone-400">
              Save a paper from the{' '}
              <Link to="/" className="text-stone-600 underline hover:text-stone-900">
                feed
              </Link>{' '}
              and it shows up here
            </p>
          </StatusBlock>
        ) : (
          <div className="space-y-8">
            {GROUPS.filter((g) => library[g.key].length > 0).map((g) => (
              <section key={g.key} aria-labelledby={`library-${g.key}`}>
                <div className="mb-3 flex items-center gap-2">
                  <h2
                    id={`library-${g.key}`}
                    className="font-display text-lg font-semibold text-stone-900"
                  >
                    {g.label}
                  </h2>
                  <Chip>{library[g.key].length}</Chip>
                </div>
                <FeedList items={library[g.key]} signedIn offerImplementing />
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Settings: edit the feed profile with the onboarding form.
import { useSession } from '@/lib/auth'
import { notify } from '@/lib/notifications'
import { useUpdateFeedProfile } from '../api/update-feed-profile'
import FeedProfileForm from './FeedProfileForm'

export default function FeedProfileSection() {
  const profile = useSession().me?.preferences?.feed_profile
  const update = useUpdateFeedProfile()

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-6">
      <h2 className="font-display mb-1 text-lg font-semibold text-stone-900">Feed profile</h2>
      <p className="mb-4 text-xs text-stone-400">
        Categories, compute setup and keywords that shape your weekly digest
      </p>
      <FeedProfileForm
        key={JSON.stringify(profile ?? null)}
        initialValue={profile ?? undefined}
        isSubmitting={update.isPending}
        submitLabel="Save"
        onSubmit={(next) =>
          update.mutate(next, {
            onSuccess: () => notify.success('Feed profile saved'),
            onError: () => notify.error('Could not save your profile'),
          })
        }
      />
    </div>
  )
}

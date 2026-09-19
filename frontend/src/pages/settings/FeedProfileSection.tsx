import { toast } from 'sonner'
import { useUpdateFeedProfile } from '../../api/users'
import FeedProfileForm from '../../components/onboarding/FeedProfileForm'
import { useUserStore } from '../../stores/userStore'

export default function FeedProfileSection() {
  const profile = useUserStore((s) => s.me?.preferences?.feed_profile)
  const update = useUpdateFeedProfile()

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6">
      <h2 className="font-display text-lg font-semibold text-stone-900 mb-1">Feed profile</h2>
      <p className="text-xs text-stone-400 mb-4">
        Categories, compute setup and keywords that shape your weekly digest
      </p>
      <FeedProfileForm
        key={JSON.stringify(profile ?? null)}
        initialValue={profile ?? undefined}
        isSubmitting={update.isPending}
        submitLabel="Save"
        onSubmit={(next) =>
          update.mutate(next, {
            onSuccess: () => toast.success('Feed profile saved'),
            onError: () => toast.error('Could not save your profile'),
          })
        }
      />
    </div>
  )
}

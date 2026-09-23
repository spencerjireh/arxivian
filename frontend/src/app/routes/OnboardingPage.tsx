// /onboarding route: the feed profile form, outside the app shell; reached from the feed prompt or Settings.
import { Navigate, useNavigate } from 'react-router-dom'
import logoIcon from '@/assets/logo-icon.png'
import { useUpdateFeedProfile } from '@/features/profile/api/update-feed-profile'
import FeedProfileForm from '@/features/profile/components/FeedProfileForm'
import { useSession } from '@/lib/auth'
import { notify } from '@/lib/notifications'

export default function OnboardingPage() {
  const { me } = useSession()
  const navigate = useNavigate()
  const update = useUpdateFeedProfile()

  if (me?.onboarded) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="paper-grain flex min-h-screen items-center justify-center bg-[var(--color-cream)] p-6">
      <div className="animate-fade-in-up relative z-10 w-full max-w-2xl rounded-xl border border-stone-200 bg-white p-8 shadow-md">
        <div className="mb-6 flex items-center gap-3">
          <img src={logoIcon} alt="" className="h-8 w-auto" aria-hidden="true" />
          <div>
            <h1 className="font-display text-2xl font-semibold text-stone-900">
              Shape your first digest
            </h1>
            <p className="text-sm text-stone-500">
              About 30 seconds. You can change this later in Settings.
            </p>
          </div>
        </div>
        <FeedProfileForm
          initialValue={me?.preferences?.feed_profile ?? undefined}
          isSubmitting={update.isPending}
          submitLabel="Build my feed"
          onSubmit={(profile) =>
            update.mutate(profile, {
              onSuccess: () => void navigate('/', { replace: true }),
              onError: () => notify.error('Could not save your profile'),
            })
          }
        />
      </div>
    </div>
  )
}

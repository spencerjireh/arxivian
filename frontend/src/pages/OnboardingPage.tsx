import { Navigate, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useUpdateFeedProfile } from '../api/users'
import FeedProfileForm from '../components/onboarding/FeedProfileForm'
import { useUserStore } from '../stores/userStore'
import logoIcon from '../assets/logo-icon.png'

export default function OnboardingPage() {
  const me = useUserStore((s) => s.me)
  const navigate = useNavigate()
  const update = useUpdateFeedProfile()

  if (me?.onboarded) {
    return <Navigate to="/feed" replace />
  }

  return (
    <div className="min-h-screen bg-[var(--color-cream)] paper-grain flex items-center justify-center p-6">
      <div className="relative z-10 w-full max-w-2xl bg-white rounded-xl border border-stone-200 shadow-md p-8 animate-fade-in-up">
        <div className="flex items-center gap-3 mb-6">
          <img src={logoIcon} alt="" className="h-8 w-auto" aria-hidden="true" />
          <div>
            <h1 className="font-display text-2xl font-semibold text-stone-900">Shape your first digest</h1>
            <p className="text-sm text-stone-500">About 30 seconds. You can change this later in Settings.</p>
          </div>
        </div>
        <FeedProfileForm
          initialValue={me?.preferences?.feed_profile ?? undefined}
          isSubmitting={update.isPending}
          submitLabel="Build my feed"
          onSubmit={(profile) =>
            update.mutate(profile, {
              onSuccess: () => navigate('/feed', { replace: true }),
              onError: () => toast.error('Could not save your profile'),
            })
          }
        />
      </div>
    </div>
  )
}

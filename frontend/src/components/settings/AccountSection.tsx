// Settings: account details, daily chat usage and sign-out.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import clsx from 'clsx'
import { LogOut, Trash2 } from 'lucide-react'
import Button from '../ui/Button'
import { useUserStore } from '../../stores/userStore'

export default function AccountSection() {
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()

  const me = useUserStore((s) => s.me)
  const clearUserStore = useUserStore((s) => s.clear)

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  if (!user) return null

  const handleSignOut = async () => {
    clearUserStore()
    await signOut()
    await navigate('/')
  }

  const handleDeleteAccount = async () => {
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await user.delete()
      await navigate('/sign-in')
    } catch (err) {
      setIsDeleting(false)
      const message = err instanceof Error ? err.message : 'Failed to delete account'
      setDeleteError(message)
    }
  }

  const displayName = user.fullName || 'User'
  const email = user.primaryEmailAddress?.emailAddress || ''
  const joinedDate = user.createdAt
    ? new Date(user.createdAt).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : ''

  return (
    <div className="rounded-xl border border-stone-200 bg-white p-6">
      <h2 className="font-display mb-4 text-lg font-semibold text-stone-900">Account</h2>

      <div className="mb-6 flex items-center gap-4">
        <img src={user.imageUrl} alt="" className="h-12 w-12 rounded-full ring-2 ring-stone-200" />
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-stone-900">{displayName}</p>
            {me && (
              <span
                className={clsx(
                  'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                  me.tier === 'pro' ? 'bg-stone-900 text-white' : 'bg-stone-100 text-stone-600'
                )}
              >
                {me.tier === 'pro' ? 'Pro' : 'Free'}
              </span>
            )}
          </div>
          <p className="text-sm text-stone-500">{email}</p>
          {joinedDate && <p className="mt-0.5 text-xs text-stone-400">Joined {joinedDate}</p>}
        </div>
      </div>

      {me && (
        <div className="mb-6 rounded-lg border border-stone-100 bg-stone-50 p-4">
          <h3 className="mb-3 text-xs font-medium tracking-wide text-stone-500 uppercase">Usage</h3>
          <div>
            <p className="text-xs text-stone-500">Daily chats</p>
            <p className="text-sm font-medium text-stone-800">
              {me.chats_used_today} / {me.daily_chat_limit ?? 'Generous'}
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleSignOut}
          leftIcon={<LogOut className="h-3.5 w-3.5" strokeWidth={1.5} />}
        >
          Sign out
        </Button>

        {showDeleteConfirm ? (
          <div className="flex items-center gap-2">
            <p className="text-xs text-stone-500">Delete your account? This cannot be undone.</p>
            {deleteError && <p className="text-xs text-red-600">{deleteError}</p>}
            <Button variant="danger" size="sm" onClick={handleDeleteAccount} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Confirm delete'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowDeleteConfirm(false)
                setDeleteError(null)
              }}
              disabled={isDeleting}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowDeleteConfirm(true)}
            leftIcon={<Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />}
          >
            Delete account
          </Button>
        )}
      </div>
    </div>
  )
}

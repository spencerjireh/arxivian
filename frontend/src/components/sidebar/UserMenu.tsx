import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import clsx from 'clsx'
import { ChevronUp, LogOut, Trash2 } from 'lucide-react'
import { useUserStore } from '../../stores/userStore'

export default function UserMenu() {
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()

  const [isOpen, setIsOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const handleClickOutside = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) {
        setIsOpen(false)
        setShowDeleteConfirm(false)
      }
    }

    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [isOpen])

  const clearUserStore = useUserStore((s) => s.clear)

  const handleSignOut = async () => {
    clearUserStore()
    await signOut()
    navigate('/sign-in')
  }

  const handleDeleteAccount = async () => {
    if (!user) return

    setIsDeleting(true)
    setDeleteError(null)
    try {
      await user.delete()
      navigate('/sign-in')
    } catch (err) {
      setIsDeleting(false)
      const message = err instanceof Error ? err.message : 'Failed to delete account'
      setDeleteError(message)
    }
  }

  if (!user) return null

  const displayName = user.fullName || user.primaryEmailAddress?.emailAddress || 'User'

  return (
    <div ref={menuRef} className="relative">
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-1 bg-white border border-stone-200 rounded-lg shadow-lg py-1 z-50">
          {showDeleteConfirm ? (
            <div className="px-3 py-2">
              <p className="text-xs text-stone-500 mb-2">Delete your account? This cannot be undone.</p>
              {deleteError && (
                <p className="text-xs text-red-600 mb-2">{deleteError}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={(e) => {
                    e.nativeEvent.stopImmediatePropagation()
                    handleDeleteAccount()
                  }}
                  disabled={isDeleting}
                  className="px-2.5 py-1.5 text-xs font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50"
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
                <button
                  onClick={(e) => {
                    e.nativeEvent.stopImmediatePropagation()
                    setShowDeleteConfirm(false)
                    setDeleteError(null)
                  }}
                  disabled={isDeleting}
                  className="px-2.5 py-1.5 text-xs font-medium rounded-lg text-stone-600 hover:bg-stone-100 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <button
                onClick={handleSignOut}
                className="w-full px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-50 flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" strokeWidth={1.5} />
                Sign out
              </button>
              <button
                onClick={(e) => {
                  e.nativeEvent.stopImmediatePropagation()
                  setShowDeleteConfirm(true)
                }}
                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                Delete account
              </button>
            </>
          )}
        </div>
      )}

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 w-full px-2 py-2 rounded-lg hover:bg-stone-100 transition-colors"
      >
        <img
          src={user.imageUrl}
          alt=""
          className="w-8 h-8 rounded-full ring-2 ring-stone-200"
        />
        <div className="flex-1 text-left min-w-0">
          <p className="text-sm font-medium text-stone-900 truncate">
            {displayName}
          </p>
        </div>
        <ChevronUp
          className={clsx('w-4 h-4 text-stone-400 transition-transform', !isOpen && 'rotate-180')}
          strokeWidth={1.5}
        />
      </button>
    </div>
  )
}

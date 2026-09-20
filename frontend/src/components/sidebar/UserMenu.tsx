// App shell: avatar button with the user name and a sign-out action.
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import clsx from 'clsx'
import { ChevronUp, LogOut } from 'lucide-react'
import { useUserStore } from '../../stores/userStore'

export default function UserMenu() {
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()

  const [isOpen, setIsOpen] = useState(false)

  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const handleClickOutside = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [isOpen])

  const clearUserStore = useUserStore((s) => s.clear)

  const handleSignOut = async () => {
    clearUserStore()
    await signOut()
    await navigate('/sign-in')
  }

  if (!user) return null

  const displayName = user.fullName || user.primaryEmailAddress?.emailAddress || 'User'

  return (
    <div ref={menuRef} className="relative">
      {isOpen && (
        <div className="absolute right-0 bottom-full left-0 z-50 mb-1 rounded-lg border border-stone-200 bg-white py-1 shadow-lg">
          <button
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-50"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.5} />
            Sign out
          </button>
        </div>
      )}

      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-stone-100"
      >
        <img src={user.imageUrl} alt="" className="h-8 w-8 rounded-full ring-2 ring-stone-200" />
        <div className="min-w-0 flex-1 text-left">
          <p className="truncate text-sm font-medium text-stone-900">{displayName}</p>
        </div>
        <ChevronUp
          className={clsx('h-4 w-4 text-stone-400 transition-transform', !isOpen && 'rotate-180')}
          strokeWidth={1.5}
        />
      </button>
    </div>
  )
}

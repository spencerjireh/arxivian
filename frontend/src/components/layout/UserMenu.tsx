// App shell: avatar button in the top nav with a sign-out dropdown.
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import clsx from 'clsx'
import { ChevronDown, LogOut } from 'lucide-react'
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
    await navigate('/')
  }

  if (!user) return null

  const displayName = user.fullName || user.primaryEmailAddress?.emailAddress || 'User'

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Account menu"
        className="flex items-center gap-2 rounded-lg px-1.5 py-1 transition-colors hover:bg-stone-100"
      >
        <img src={user.imageUrl} alt="" className="h-7 w-7 rounded-full ring-2 ring-stone-200" />
        <ChevronDown
          className={clsx('h-4 w-4 text-stone-400 transition-transform', isOpen && 'rotate-180')}
          strokeWidth={1.5}
        />
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute top-full right-0 z-50 mt-1 w-56 rounded-lg border border-stone-200 bg-white py-1 shadow-lg"
        >
          <p className="truncate px-3 py-2 text-sm font-medium text-stone-900">{displayName}</p>
          <button
            role="menuitem"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-stone-700 hover:bg-stone-50"
          >
            <LogOut className="h-4 w-4" strokeWidth={1.5} />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

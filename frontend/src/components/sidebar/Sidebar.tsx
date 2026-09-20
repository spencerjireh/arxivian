// App shell: Feed / Library / Settings navigation and the user menu.
import { useNavigate, useLocation } from 'react-router-dom'
import { PanelLeftClose, BookOpen, Settings, Newspaper } from 'lucide-react'
import clsx from 'clsx'
import { useSidebarStore } from '../../stores/sidebarStore'
import UserMenu from './UserMenu'
import Button from '../ui/Button'
import { matchesNav } from '../../lib/nav'
import logoIcon from '../../assets/logo-icon.png'

const navItems = [
  { path: '/feed', label: 'Feed', icon: Newspaper },
  { path: '/library', label: 'Library', icon: BookOpen },
  { path: '/settings', label: 'Settings', icon: Settings },
] as const

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const close = useSidebarStore((state) => state.close)

  return (
    <div className="flex h-screen w-72 flex-col border-r border-stone-200 bg-stone-50">
      <div className="border-b border-stone-200 px-4 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src={logoIcon} alt="" className="h-6 w-auto" aria-hidden="true" />
            <h1 className="font-display text-xl font-semibold tracking-tight text-stone-900">
              Arxivian
              <span className="ml-2 rounded bg-stone-100 px-1.5 py-0.5 font-mono text-[10px] font-normal tracking-wider text-stone-400 uppercase">
                Beta
              </span>
            </h1>
          </div>
          <Button variant="ghost" size="sm" onClick={close} aria-label="Close sidebar">
            <PanelLeftClose className="h-5 w-5" strokeWidth={1.5} />
          </Button>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-3">
        {navItems.map(({ path, label, icon: Icon }) => {
          const isActive = matchesNav(path, location.pathname)
          return (
            <Button
              key={path}
              variant="ghost"
              size="md"
              className={clsx(
                'w-full justify-start',
                isActive && 'bg-stone-100 font-medium text-stone-900'
              )}
              onClick={() => navigate(path)}
              leftIcon={<Icon className="h-4 w-4" strokeWidth={1.5} />}
            >
              {label}
            </Button>
          )
        })}
      </nav>

      <div className="border-t border-stone-200 px-2 py-3">
        <UserMenu />
      </div>
    </div>
  )
}

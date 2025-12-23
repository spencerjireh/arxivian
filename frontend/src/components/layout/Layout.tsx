import { Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import Sidebar from '../sidebar/Sidebar'
import SidebarToggle from '../sidebar/SidebarToggle'
import { useSidebarStore } from '../../stores/sidebarStore'

const Layout = () => {
  const location = useLocation()
  const isOpen = useSidebarStore((state) => state.isOpen)
  const shouldReduceMotion = useReducedMotion()

  const springTransition = { type: 'spring' as const, stiffness: 400, damping: 30 }
  const fastTransition = { duration: 0.15, ease: 'easeOut' as const }

  // Use stable key for chat pages to prevent unmount/remount during session transitions
  // Only animate between truly different page types (welcome vs chat)
  const pageKey = location.pathname === '/' ? 'welcome' : 'chat'

  return (
    <div className="h-screen bg-[#FAFAF9] flex overflow-hidden">
      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.aside
            key="sidebar"
            initial={shouldReduceMotion ? false : { opacity: 0, x: -280 }}
            animate={{ opacity: 1, x: 0 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0, x: -280 }}
            transition={shouldReduceMotion ? { duration: 0 } : springTransition}
          >
            <Sidebar />
          </motion.aside>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {!isOpen && (
          <motion.div
            key="toggle"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0 }}
            transition={shouldReduceMotion ? { duration: 0 } : fastTransition}
          >
            <SidebarToggle />
          </motion.div>
        )}
      </AnimatePresence>
      <main className="flex-1 flex flex-col min-w-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={pageKey}
            className="flex-1 flex flex-col"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0 }}
            transition={shouldReduceMotion ? { duration: 0 } : fastTransition}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}

export default Layout

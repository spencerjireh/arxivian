import { Outlet } from 'react-router-dom'
import Sidebar from '../sidebar/Sidebar'
import SidebarToggle from '../sidebar/SidebarToggle'
import { useSidebarStore } from '../../stores/sidebarStore'

const Layout = () => {
  const isOpen = useSidebarStore((state) => state.isOpen)

  return (
    <div className="h-screen bg-[#FAFAF9] flex overflow-hidden">
      {isOpen && <Sidebar />}
      {!isOpen && <SidebarToggle />}
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout

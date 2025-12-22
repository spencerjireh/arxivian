// Floating toggle button to open sidebar when hidden

import { PanelLeft } from 'lucide-react'
import { useSidebarStore } from '../../stores/sidebarStore'

export default function SidebarToggle() {
  const open = useSidebarStore((state) => state.open)

  return (
    <button
      onClick={open}
      className="
        fixed top-4 left-4 z-50
        p-2.5 bg-white border border-stone-200 rounded-lg
        text-stone-500 hover:text-stone-700 hover:bg-stone-50
        shadow-sm hover:shadow
        transition-all duration-150
      "
      title="Open sidebar"
    >
      <PanelLeft className="w-5 h-5" strokeWidth={1.5} />
    </button>
  )
}

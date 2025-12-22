import { PanelLeft } from 'lucide-react'
import { useSidebarStore } from '../../stores/sidebarStore'
import Button from '../ui/Button'

export default function SidebarToggle() {
  const open = useSidebarStore((state) => state.open)

  return (
    <div className="fixed top-4 left-4 z-50">
      <Button
        variant="secondary"
        size="sm"
        onClick={open}
        aria-label="Open sidebar"
        className="shadow-sm hover:shadow"
      >
        <PanelLeft className="w-5 h-5" strokeWidth={1.5} />
      </Button>
    </div>
  )
}

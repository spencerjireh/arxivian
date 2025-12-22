import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'

const Header = () => {
  return (
    <header className="bg-white/80 backdrop-blur-sm border-b border-stone-100 sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-6 sm:px-8">
        <div className="flex items-center h-16">
          <Link
            to="/"
            className="flex items-center gap-3 group"
          >
            <div className="w-8 h-8 rounded-lg bg-stone-900 flex items-center justify-center transition-transform duration-200 group-hover:scale-105">
              <BookOpen className="w-4 h-4 text-white" strokeWidth={1.5} />
            </div>
            <span className="font-display text-xl text-stone-900 tracking-tight">
              Jirehs Agent
            </span>
          </Link>
        </div>
      </div>
    </header>
  )
}

export default Header

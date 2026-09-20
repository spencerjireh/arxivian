// Public pages: site footer with the privacy link.
import { Link } from 'react-router-dom'

const Footer = () => {
  return (
    <footer className="border-t border-stone-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex items-center justify-center gap-3 text-sm text-stone-500">
          <p>2026 Arxivian. Built for researchers.</p>
          <span className="text-stone-300" aria-hidden="true">
            |
          </span>
          <Link to="/privacy" className="transition-colors duration-150 hover:text-stone-900">
            Privacy
          </Link>
        </div>
      </div>
    </footer>
  )
}

export default Footer

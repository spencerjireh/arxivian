import { Link } from 'react-router-dom'

const Footer = () => {
  return (
    <footer className="bg-white border-t border-stone-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-center gap-3 text-stone-500 text-sm">
          <p>2026 Arxivian. Built for researchers.</p>
          <span className="text-stone-300" aria-hidden="true">|</span>
          <Link
            to="/privacy"
            className="hover:text-stone-900 transition-colors duration-150"
          >
            Privacy
          </Link>
        </div>
      </div>
    </footer>
  )
}

export default Footer

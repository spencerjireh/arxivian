// 404 page.
import { useNavigate } from 'react-router-dom'
import { BookX } from 'lucide-react'
import Button from '../components/ui/Button'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="paper-grain flex min-h-screen items-center justify-center bg-[var(--color-cream)] p-6">
      <div className="animate-fade-in-up relative z-10 w-full max-w-md rounded-xl border border-stone-200 bg-white p-8 text-center shadow-md">
        <p className="font-display mb-4 text-7xl font-semibold text-stone-200 select-none">404</p>

        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100">
          <BookX className="h-5 w-5 text-stone-400" strokeWidth={1.5} />
        </div>

        <h1 className="font-display mb-2 text-2xl font-semibold text-stone-900">Page not found</h1>

        <div className="mx-auto mb-4 h-0.5 w-8 bg-[var(--color-accent)]" />

        <p className="mb-6 text-sm leading-relaxed text-stone-500">
          The page you are looking for does not exist or has been moved.
        </p>

        <div className="flex items-center justify-center gap-3">
          <Button variant="primary" size="md" onClick={() => navigate(-1)}>
            Go back
          </Button>
          <Button variant="secondary" size="md" onClick={() => navigate('/')}>
            Return home
          </Button>
        </div>
      </div>
    </div>
  )
}

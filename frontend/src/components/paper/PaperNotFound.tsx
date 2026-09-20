// Paper detail: 404 state for an unknown arXiv id.
import { Link } from 'react-router-dom'
import { BookX } from 'lucide-react'

interface PaperNotFoundProps {
  arxivId: string
}

export default function PaperNotFound({ arxivId }: PaperNotFoundProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100">
        <BookX className="h-5 w-5 text-stone-400" strokeWidth={1.5} />
      </div>
      <p className="text-sm font-medium text-stone-700">Paper not found</p>
      <p className="mt-1 text-sm text-stone-400">
        <span className="font-mono">{arxivId}</span> is not a valid arXiv identifier.
      </p>
      <Link to="/feed" className="mt-4 text-sm text-stone-600 underline underline-offset-2">
        Back to feed
      </Link>
    </div>
  )
}

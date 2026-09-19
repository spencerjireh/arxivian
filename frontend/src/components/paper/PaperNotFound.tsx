import { Link } from 'react-router-dom'
import { BookX } from 'lucide-react'

interface PaperNotFoundProps {
  arxivId: string
}

export default function PaperNotFound({ arxivId }: PaperNotFoundProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mb-3">
        <BookX className="w-5 h-5 text-stone-400" strokeWidth={1.5} />
      </div>
      <p className="text-sm font-medium text-stone-700">Paper not found</p>
      <p className="text-sm text-stone-400 mt-1">
        <span className="font-mono">{arxivId}</span> is not a valid arXiv identifier.
      </p>
      <Link to="/feed" className="text-sm text-stone-600 underline underline-offset-2 mt-4">
        Back to feed
      </Link>
    </div>
  )
}

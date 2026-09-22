// The one markdown entry point: lazily loads MarkdownBody, shows a streaming cursor.
import { lazy, Suspense } from 'react'
import clsx from 'clsx'

const MarkdownBody = lazy(() => import('./MarkdownBody'))

interface MarkdownRendererProps {
  content: string
  streamingCursor?: React.ReactNode
}

/** GFM + math + arXiv links, always on. Shows the raw text until the body chunk loads. */
export default function MarkdownRenderer({ content, streamingCursor }: MarkdownRendererProps) {
  return (
    <div
      className={clsx(
        'markdown-content',
        streamingCursor && '[&_p:last-of-type]:mb-0 [&_p:last-of-type]:inline'
      )}
    >
      <Suspense fallback={<p className="whitespace-pre-wrap">{content}</p>}>
        <MarkdownBody content={content || ''} />
      </Suspense>
      {streamingCursor}
    </div>
  )
}

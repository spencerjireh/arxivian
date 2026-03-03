import { lazy, Suspense, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import clsx from 'clsx'
import { remarkPluginsBase, rehypePluginsBase } from '../../lib/markdown/config.base'
import { markdownComponentsBase } from '../../lib/markdown/components.base'
import { needsEnhancedRenderer } from '../../lib/markdown/detect'
import ErrorBoundary from '../ui/ErrorBoundary'

const EnhancedMarkdownRenderer = lazy(() => import('./EnhancedMarkdownRenderer'))

interface MarkdownRendererProps {
  content: string
  streamingCursor?: React.ReactNode
}

function BaseRenderer({ content, streamingCursor }: MarkdownRendererProps) {
  return (
    <>
      <ErrorBoundary fallback={<pre className="text-sm text-stone-500 whitespace-pre-wrap">{content}</pre>}>
        <ReactMarkdown
          remarkPlugins={remarkPluginsBase}
          rehypePlugins={rehypePluginsBase}
          components={markdownComponentsBase}
        >
          {content}
        </ReactMarkdown>
      </ErrorBoundary>
      {streamingCursor}
    </>
  )
}

export default function MarkdownRenderer({ content, streamingCursor }: MarkdownRendererProps) {
  const [enhanced, setEnhanced] = useState(false)
  if (!enhanced && needsEnhancedRenderer(content || '')) {
    setEnhanced(true)
  }

  return (
    <div
      className={clsx(
        'markdown-content',
        streamingCursor && '[&_p:last-of-type]:inline [&_p:last-of-type]:mb-0'
      )}
    >
      {enhanced ? (
        <Suspense fallback={<BaseRenderer content={content} streamingCursor={streamingCursor} />}>
          <EnhancedMarkdownRenderer content={content} streamingCursor={streamingCursor} />
        </Suspense>
      ) : (
        <BaseRenderer content={content} streamingCursor={streamingCursor} />
      )}
    </div>
  )
}

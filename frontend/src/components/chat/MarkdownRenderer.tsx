import ReactMarkdown from 'react-markdown'
import clsx from 'clsx'
import { markdownComponents, remarkPlugins, rehypePlugins } from '../../lib/markdown'
import ErrorBoundary from '../ui/ErrorBoundary'
import 'katex/dist/katex.min.css'

interface MarkdownRendererProps {
  content: string
  streamingCursor?: React.ReactNode
}

export default function MarkdownRenderer({ content, streamingCursor }: MarkdownRendererProps) {

  return (
    <div
      className={clsx(
        'markdown-content',
        streamingCursor && '[&_p:last-of-type]:inline [&_p:last-of-type]:mb-0'
      )}
    >
      <ErrorBoundary fallback={<pre className="text-sm text-stone-500 whitespace-pre-wrap">{content}</pre>}>
        <ReactMarkdown
          remarkPlugins={remarkPlugins}
          rehypePlugins={rehypePlugins}
          components={markdownComponents}
        >
          {content || ''}
        </ReactMarkdown>
      </ErrorBoundary>
      {streamingCursor}
    </div>
  )
}

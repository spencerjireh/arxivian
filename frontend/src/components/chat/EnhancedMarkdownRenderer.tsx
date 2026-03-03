import ReactMarkdown from 'react-markdown'
import { remarkPluginsEnhanced, rehypePluginsEnhanced } from '../../lib/markdown/config.enhanced'
import { markdownComponentsEnhanced } from '../../lib/markdown/components.enhanced'
import { preprocessLatex } from '../../lib/markdown/preprocessors'
import ErrorBoundary from '../ui/ErrorBoundary'
import 'katex/dist/katex.min.css'

interface EnhancedMarkdownRendererProps {
  content: string
  streamingCursor?: React.ReactNode
}

export default function EnhancedMarkdownRenderer({
  content,
  streamingCursor,
}: EnhancedMarkdownRendererProps) {
  const processed = preprocessLatex(content || '')

  return (
    <>
      <ErrorBoundary fallback={<pre className="text-sm text-stone-500 whitespace-pre-wrap">{content}</pre>}>
        <ReactMarkdown
          remarkPlugins={remarkPluginsEnhanced}
          rehypePlugins={rehypePluginsEnhanced}
          components={markdownComponentsEnhanced}
        >
          {processed}
        </ReactMarkdown>
      </ErrorBoundary>
      {streamingCursor}
    </>
  )
}

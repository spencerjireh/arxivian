import ReactMarkdown from 'react-markdown'
import { markdownComponents, remarkPlugins, rehypePlugins } from '../../lib/markdown'
import 'katex/dist/katex.min.css'

interface MarkdownRendererProps {
  content: string
  streamingCursor?: React.ReactNode
}

export default function MarkdownRenderer({ content, streamingCursor }: MarkdownRendererProps) {

  return (
    <div
      className={`markdown-content ${streamingCursor ? '[&_p:last-of-type]:inline [&_p:last-of-type]:mb-0' : ''}`}
    >
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={markdownComponents}
      >
        {content || ''}
      </ReactMarkdown>
      {streamingCursor}
    </div>
  )
}

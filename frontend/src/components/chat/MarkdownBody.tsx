import ReactMarkdown, { type Components } from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { remarkPlugins, rehypePlugins } from '../../lib/markdown/config'
import { markdownComponents } from '../../lib/markdown/components'
import { preprocessLatex } from '../../lib/markdown/preprocessors'
import ErrorBoundary from '../ui/ErrorBoundary'
import 'katex/dist/katex.min.css'

interface MarkdownBodyProps {
  content: string
}

const components: Components = {
  ...markdownComponents,
  code: (props) => {
    const { children, className, node, ...rest } = props
    const match = /language-(\w+)/.exec(className || '')
    return node?.position && match ? (
      <div className="my-4 rounded-lg overflow-hidden">
        <SyntaxHighlighter
          style={oneDark as { [key: string]: React.CSSProperties }}
          language={match[1]}
          PreTag="div"
          customStyle={{ margin: 0, borderRadius: '0.75rem', fontSize: '0.875rem' }}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    ) : (
      <code className="bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded text-sm font-mono" {...rest}>
        {children}
      </code>
    )
  },
}

/** The heavy half of the renderer (KaTeX + Prism); loaded lazily by MarkdownRenderer. */
export default function MarkdownBody({ content }: MarkdownBodyProps) {
  return (
    <ErrorBoundary
      fallback={<pre className="text-sm text-stone-500 whitespace-pre-wrap">{content}</pre>}
    >
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {preprocessLatex(content)}
      </ReactMarkdown>
    </ErrorBoundary>
  )
}

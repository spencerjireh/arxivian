import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'
import { markdownComponentsBase } from './components.base'

/**
 * Enhanced components: spreads all base components, then overrides `code`
 * with SyntaxHighlighter and adds math-aware `div`/`span` wrappers.
 */
export const markdownComponentsEnhanced: Components = {
  ...markdownComponentsBase,

  code: (props) => {
    const { children, className, node, ...rest } = props
    const match = /language-(\w+)/.exec(className || '')
    const language = match ? match[1] : ''
    const isInline = !node?.position

    return !isInline && language ? (
      <div className="my-4 rounded-lg overflow-hidden">
        <SyntaxHighlighter
          style={oneDark as { [key: string]: React.CSSProperties }}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            borderRadius: '0.75rem',
            fontSize: '0.875rem',
          }}
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

  div: ({ className, children, ...props }) => {
    if (className === 'math math-display') {
      return (
        <div className="math-display my-6 overflow-x-auto overflow-y-hidden" {...props}>
          {children}
        </div>
      )
    }
    return <div className={className} {...props}>{children}</div>
  },

  span: ({ className, children, ...props }) => {
    if (className === 'math math-inline') {
      return (
        <span className="math-inline text-stone-800" {...props}>
          {children}
        </span>
      )
    }
    return <span className={className} {...props}>{children}</span>
  },
}

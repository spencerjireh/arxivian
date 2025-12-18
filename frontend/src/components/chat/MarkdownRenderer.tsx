// Markdown renderer with syntax highlighting and custom styling

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'
import 'katex/dist/katex.min.css'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const components: Components = {
    // Headings
    h1: ({ children }) => (
      <h1 className="text-2xl font-bold mb-3 mt-4 text-gray-900">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-xl font-bold mb-2 mt-3 text-gray-900">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-lg font-semibold mb-2 mt-3 text-gray-900">{children}</h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-base font-semibold mb-1 mt-2 text-gray-900">{children}</h4>
    ),
    h5: ({ children }) => (
      <h5 className="text-sm font-semibold mb-1 mt-2 text-gray-900">{children}</h5>
    ),
    h6: ({ children }) => (
      <h6 className="text-xs font-semibold mb-1 mt-2 text-gray-900">{children}</h6>
    ),

    // Paragraphs
    p: ({ children }) => <p className="mb-3 last:mb-0 text-gray-800 leading-relaxed">{children}</p>,

    // Links - open in new tab with external icon
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-600 hover:text-blue-800 underline hover:no-underline inline-flex items-center gap-1"
      >
        {children}
        <svg
          className="w-3 h-3 inline-block"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
          />
        </svg>
      </a>
    ),

    // Lists
    ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
    li: ({ children }) => <li className="text-gray-800 leading-relaxed">{children}</li>,

    // Blockquotes
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-gray-300 pl-4 py-2 my-3 bg-gray-50 italic text-gray-700">
        {children}
      </blockquote>
    ),

    // Code blocks with syntax highlighting
    code: (props) => {
      const { children, className, node, ...rest } = props
      const match = /language-(\w+)/.exec(className || '')
      const language = match ? match[1] : ''
      const isInline = !node?.position

      return !isInline && language ? (
        <div className="my-3 rounded-lg overflow-hidden">
          <SyntaxHighlighter
            style={oneDark as { [key: string]: React.CSSProperties }}
            language={language}
            PreTag="div"
          >
            {String(children).replace(/\n$/, '')}
          </SyntaxHighlighter>
        </div>
      ) : (
        <code
          className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono"
          {...rest}
        >
          {children}
        </code>
      )
    },

    // Tables
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
    tbody: ({ children }) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
    tr: ({ children }) => <tr>{children}</tr>,
    th: ({ children }) => (
      <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-2 text-sm text-gray-800 whitespace-normal">{children}</td>
    ),

    // Horizontal rule
    hr: () => <hr className="my-4 border-gray-200" />,

    // Strong and emphasis
    strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
    em: ({ children }) => <em className="italic">{children}</em>,

    // Strikethrough (from GFM)
    del: ({ children }) => <del className="line-through text-gray-600">{children}</del>,

    // Pre tag (for code block wrapper)
    pre: ({ children }) => <>{children}</>,
  }

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {content || ''}
      </ReactMarkdown>
    </div>
  )
}

// Markdown renderer with syntax highlighting and custom styling

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'
import { ExternalLink } from 'lucide-react'
import 'katex/dist/katex.min.css'

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const components: Components = {
    // Headings - using display font
    h1: ({ children }) => (
      <h1 className="font-display text-2xl text-stone-900 mb-4 mt-6 first:mt-0 leading-tight">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="font-display text-xl text-stone-900 mb-3 mt-5 first:mt-0 leading-tight">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="font-display text-lg text-stone-900 mb-2 mt-4 first:mt-0 leading-snug">
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="font-medium text-base text-stone-900 mb-2 mt-4 first:mt-0">
        {children}
      </h4>
    ),
    h5: ({ children }) => (
      <h5 className="font-medium text-sm text-stone-900 mb-1.5 mt-3 first:mt-0">
        {children}
      </h5>
    ),
    h6: ({ children }) => (
      <h6 className="font-medium text-xs text-stone-700 mb-1 mt-3 first:mt-0 uppercase tracking-wide">
        {children}
      </h6>
    ),

    // Paragraphs
    p: ({ children }) => (
      <p className="text-stone-700 leading-relaxed mb-4 last:mb-0">{children}</p>
    ),

    // Links - external with subtle indicator
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-stone-900 underline decoration-stone-300 underline-offset-2 hover:decoration-stone-500 transition-colors duration-150 inline-flex items-center gap-0.5"
      >
        {children}
        <ExternalLink className="w-3 h-3 text-stone-400 flex-shrink-0" strokeWidth={1.5} />
      </a>
    ),

    // Lists
    ul: ({ children }) => (
      <ul className="mb-4 last:mb-0 space-y-1.5 list-none pl-0">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="mb-4 last:mb-0 space-y-1.5 list-none pl-0 counter-reset-list">
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => {
      const isOrdered = props.node?.position?.start.column === 1
      return (
        <li className="text-stone-700 leading-relaxed flex gap-2">
          <span className="text-stone-400 flex-shrink-0 select-none">
            {isOrdered ? '' : '-'}
          </span>
          <span>{children}</span>
        </li>
      )
    },

    // Blockquotes - elegant left border
    blockquote: ({ children }) => (
      <blockquote className="border-l-2 border-stone-200 pl-4 my-4 italic text-stone-600">
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
        <code
          className="bg-stone-100 text-stone-800 px-1.5 py-0.5 rounded text-sm font-mono"
          {...rest}
        >
          {children}
        </code>
      )
    },

    // Tables - minimal elegant style
    table: ({ children }) => (
      <div className="my-4 overflow-x-auto">
        <table className="w-full text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="border-b border-stone-200">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-stone-100">{children}</tbody>
    ),
    tr: ({ children }) => <tr>{children}</tr>,
    th: ({ children }) => (
      <th className="px-4 py-2.5 text-left text-xs font-medium text-stone-500 uppercase tracking-wide">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-2.5 text-stone-700 align-top">{children}</td>
    ),

    // Horizontal rule
    hr: () => <hr className="my-6 border-t border-stone-200" />,

    // Strong and emphasis
    strong: ({ children }) => (
      <strong className="font-semibold text-stone-900">{children}</strong>
    ),
    em: ({ children }) => <em className="italic">{children}</em>,

    // Strikethrough
    del: ({ children }) => (
      <del className="line-through text-stone-500">{children}</del>
    ),

    // Pre tag wrapper
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

// remark and rehype plugin lists for the markdown renderer (GFM, math, arXiv links).
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { remarkArxivLinks } from './remark-arxiv-links'
import type { PluggableList } from 'unified'

export const remarkPlugins: PluggableList = [remarkGfm, remarkMath, remarkArxivLinks]

export const rehypePlugins: PluggableList = [
  [
    rehypeKatex,
    {
      strict: false,
      trust: false,
      output: 'html',
      throwOnError: false,
      errorColor: '#B91C1C',
      macros: {
        '\\RR': '\\mathbb{R}',
        '\\NN': '\\mathbb{N}',
        '\\ZZ': '\\mathbb{Z}',
        '\\QQ': '\\mathbb{Q}',
        '\\CC': '\\mathbb{C}',
      },
    },
  ],
]

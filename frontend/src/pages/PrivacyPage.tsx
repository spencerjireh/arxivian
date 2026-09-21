// /privacy route: renders content/privacy-policy.md through the markdown component map.
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'
import { markdownComponents } from '../lib/markdown/components'
import { headingComponents } from '../lib/markdownHeadings'
import policy from '../content/privacy-policy.md?raw'

const components = headingComponents(markdownComponents)

export default function PrivacyPage() {
  return (
    <div className="paper-grain flex min-h-screen flex-col bg-[#FAFAF9]">
      <PublicHeader />

      <article className="animate-fade-in mx-auto max-w-2xl flex-1 px-4 pt-20 pb-24 sm:px-6 lg:px-8">
        <p className="mb-4 text-sm font-medium tracking-wider text-stone-500 uppercase">Legal</p>
        <div className="markdown-content text-sm leading-relaxed text-stone-600">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
            {policy}
          </ReactMarkdown>
        </div>
      </article>

      <Footer />
    </div>
  )
}

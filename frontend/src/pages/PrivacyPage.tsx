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
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col paper-grain">
      <PublicHeader />

      <article className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 flex-1 animate-fade-in">
        <p className="text-sm text-stone-500 uppercase tracking-wider font-medium mb-4">Legal</p>
        <div className="markdown-content text-sm text-stone-600 leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
            {policy}
          </ReactMarkdown>
        </div>
      </article>

      <Footer />
    </div>
  )
}

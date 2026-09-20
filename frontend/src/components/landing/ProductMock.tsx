// Landing hero: static mock of the product window shown under the headline (decorative).
import { BookOpen, ChevronRight, User, FileText } from 'lucide-react'
import logoIcon from '../../assets/logo-icon.png'

export default function ProductMock() {
  return (
    <div
      className="mock-window mx-auto max-w-2xl overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-lg"
      style={{ perspective: '1200px', transform: 'rotateX(2deg) rotateY(-1deg)' }}
      aria-hidden="true"
    >
      {/* Window chrome */}
      <div className="flex items-center gap-2 border-b border-stone-100 bg-stone-50/60 px-4 py-2.5">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
        </div>
        <div className="flex flex-1 justify-center">
          <span className="rounded-md bg-stone-100 px-3 py-0.5 font-mono text-[11px] text-stone-400">
            arxivian.app/chat
          </span>
        </div>
      </div>

      {/* Chat content */}
      <div className="space-y-6 p-5">
        {/* User message */}
        <div className="flex justify-end">
          <div className="max-w-[80%]">
            <div className="mb-3 flex items-center justify-end gap-2.5">
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                <User className="h-3.5 w-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </div>
            <div className="pr-9 text-right text-sm leading-relaxed text-stone-800">
              What are the key contributions of attention mechanisms?
            </div>
          </div>
        </div>

        {/* Agent response */}
        <div>
          <div className="mb-3 flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
              <img src={logoIcon} alt="" className="h-4 w-4" aria-hidden="true" />
            </div>
            <span className="text-sm font-medium text-stone-500">Arxivian</span>
          </div>
          <div className="space-y-4 pl-9">
            {/* Reasoning bar (static mock of ThinkingTimeline collapsed state) */}
            <div className="flex items-center gap-2 border-l-2 border-stone-200 py-1.5 pl-3 text-xs text-stone-400">
              <BookOpen className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
              <span>View reasoning</span>
              <span className="ml-auto flex items-center gap-1.5">
                <span className="italic">Searched 1 source</span>
                <span className="font-mono">-- 2.1s</span>
                <ChevronRight className="h-3.5 w-3.5" strokeWidth={1.5} />
              </span>
            </div>

            <div className="text-sm leading-relaxed text-stone-800">
              The <strong>self-attention mechanism</strong> allows models to weigh the relevance of
              each token relative to all others in a sequence, replacing recurrence entirely. This
              enables parallel computation and captures long-range dependencies more effectively.
            </div>

            {/* Sources section */}
            <div className="border-t border-stone-100 pt-4">
              <div className="mb-3 text-xs font-medium tracking-wider text-stone-400 uppercase">
                Sources
              </div>
              <div className="rounded-lg border border-stone-100">
                <div className="flex items-start gap-3 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-stone-100">
                    <FileText className="h-4 w-4 text-stone-500" strokeWidth={1.5} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="font-mono text-xs text-stone-400">1706.03762</span>
                      <span className="text-xs text-stone-300">|</span>
                      <span className="text-xs text-stone-400">96% match</span>
                    </div>
                    <p className="text-sm leading-snug text-stone-700">Attention Is All You Need</p>
                    <div className="mt-1.5 h-1 w-20 overflow-hidden rounded-full bg-stone-100">
                      <div className="h-full rounded-full bg-stone-500" style={{ width: '96%' }} />
                    </div>
                  </div>
                  <ChevronRight
                    className="mt-1 h-4 w-4 shrink-0 text-stone-300"
                    strokeWidth={1.5}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

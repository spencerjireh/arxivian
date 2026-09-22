// Landing hero: static mock of a feed card in the product window (decorative).
import { Bookmark, Check, X } from 'lucide-react'

const CHIPS = ['Pseudocode present', 'Public datasets', '1 GPU', 'Code released']

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
            arxivian.com/feed
          </span>
        </div>
      </div>

      {/* One feed card */}
      <div className="p-5">
        <div className="rounded-xl border border-stone-200 p-4 text-left">
          <div className="flex items-start gap-4">
            <div className="min-w-0 flex-1">
              <div className="mb-1 flex items-center gap-2 text-[11px] text-stone-400">
                <span className="font-mono">cs.LG</span>
                <span className="text-stone-300">|</span>
                <span>2026-09-15</span>
              </div>
              <p className="text-sm leading-snug font-medium text-stone-900">
                Sparse KV-cache eviction for long-context decoding
              </p>
              <p className="mt-1.5 text-sm text-stone-600">
                Transformer for language modeling; one consumer GPU; public data
              </p>
            </div>
            <div className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
              <span className="text-lg leading-none font-semibold">78</span>
              <span className="text-[9px] tracking-wider uppercase">score</span>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {CHIPS.map((chip) => (
              <span
                key={chip}
                className="rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-[11px] text-stone-600"
              >
                {chip}
              </span>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-2 border-t border-stone-100 pt-3 text-xs">
            <span className="inline-flex items-center gap-1 rounded-md border border-stone-200 px-2 py-1 text-stone-700">
              <Bookmark className="h-3 w-3" strokeWidth={1.5} /> Save
            </span>
            <span className="inline-flex items-center gap-1 rounded-md border border-stone-200 px-2 py-1 text-stone-700">
              <X className="h-3 w-3" strokeWidth={1.5} /> Dismiss
            </span>
            <span className="inline-flex items-center gap-1 rounded-md border border-stone-200 px-2 py-1 text-stone-700">
              <Check className="h-3 w-3" strokeWidth={1.5} /> Implementing
            </span>
            <span className="ml-auto text-stone-400">Fits your profile: single GPU</span>
          </div>
        </div>
      </div>
    </div>
  )
}

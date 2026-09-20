// Landing feature grid: one small decorative illustration per feature card.
import { AlertTriangle, BookOpen, Bookmark, Check, FolderGit2, X } from 'lucide-react'

export function WeeklyDigestIllustration() {
  return (
    <div className="relative h-24">
      {[
        {
          id: '2609.01204',
          title: 'Test-time scaling for code generation',
          score: 64,
          offset: 16,
          opacity: 0.7,
        },
        {
          id: '2609.00871',
          title: 'Rotary position interpolation revisited',
          score: 71,
          offset: 8,
          opacity: 0.85,
        },
        {
          id: '2609.00352',
          title: 'Sparse KV-cache eviction for long-context decoding',
          score: 78,
          offset: 0,
          opacity: 1,
        },
      ].map((paper) => (
        <div
          key={paper.id}
          className="absolute right-0 left-0 flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2"
          style={{ opacity: paper.opacity, top: paper.offset }}
        >
          <span className="w-7 shrink-0 text-center text-xs font-semibold text-emerald-700">
            {paper.score}
          </span>
          <span className="font-mono text-[10px] text-stone-400">{paper.id}</span>
          <span className="truncate text-xs text-stone-600">{paper.title}</span>
        </div>
      ))}
    </div>
  )
}

export function EvidenceIllustration() {
  return (
    <div className="space-y-2 rounded-lg bg-stone-50 p-3 text-xs">
      <div className="flex items-center justify-between">
        <span className="font-medium text-stone-700">Method clarity</span>
        <span className="text-[10px] text-stone-400">level 3 of 4</span>
      </div>
      <div className="flex h-1.5 gap-0.5 overflow-hidden rounded-full">
        <div className="w-[6%] bg-stone-200" />
        <div className="w-[14%] bg-stone-300" />
        <div className="w-[62%] bg-stone-600" />
        <div className="w-[18%] bg-stone-300" />
      </div>
      <blockquote className="border-l-2 border-stone-300 pl-2 text-[11px] leading-relaxed text-stone-500 italic">
        Algorithm 1 gives the full training loop; hyperparameters are listed in Table 4.
      </blockquote>
    </div>
  )
}

export function LifecycleIllustration() {
  return (
    <div className="flex flex-wrap gap-1.5 text-[11px]">
      <span className="inline-flex items-center gap-1 rounded-md border border-stone-200 bg-white px-2 py-1 text-stone-700">
        <Bookmark className="h-3 w-3" strokeWidth={1.5} /> Save
      </span>
      <span className="inline-flex items-center gap-1 rounded-md border border-stone-200 bg-white px-2 py-1 text-stone-700">
        <X className="h-3 w-3" strokeWidth={1.5} /> Dismiss
      </span>
      <span className="inline-flex items-center gap-1 rounded-md border border-stone-800 bg-stone-800 px-2 py-1 text-white">
        <Check className="h-3 w-3" strokeWidth={1.5} /> Implementing
      </span>
    </div>
  )
}

export function ScopedChatIllustration() {
  return (
    <div className="space-y-1.5 text-[11px]">
      {[
        { icon: BookOpen, text: 'Explain the core method' },
        { icon: FolderGit2, text: 'What would a minimal repo look like' },
        { icon: AlertTriangle, text: 'What are the risky parts to reproduce' },
      ].map(({ icon: Icon, text }) => (
        <div
          key={text}
          className="flex items-center gap-2 rounded-md border border-stone-200 bg-white px-2.5 py-1.5 text-stone-600"
        >
          <Icon className="h-3 w-3 shrink-0 text-stone-400" strokeWidth={1.5} />
          <span className="truncate">{text}</span>
        </div>
      ))}
    </div>
  )
}

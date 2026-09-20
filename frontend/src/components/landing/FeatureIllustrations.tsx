// Landing feature grid: one small decorative illustration per feature card.
import { ChevronDown, FileText, GitBranch, Search, User } from 'lucide-react'
import logoIcon from '../../assets/logo-icon.png'

export function ResearchAssistantIllustration() {
  return (
    <div className="space-y-3 rounded-lg bg-stone-50 p-3 text-xs">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[85%]">
          <div className="mb-1 flex items-center justify-end gap-1.5">
            <span className="text-[10px] font-medium text-stone-400">You</span>
            <div className="flex h-4 w-4 items-center justify-center rounded bg-stone-200">
              <User className="h-2.5 w-2.5 text-stone-500" strokeWidth={1.5} />
            </div>
          </div>
          <div className="pr-5 text-right text-stone-700">How does RLHF improve alignment?</div>
        </div>
      </div>
      {/* Agent message */}
      <div>
        <div className="mb-1 flex items-center gap-1.5">
          <div className="flex h-4 w-4 items-center justify-center rounded bg-stone-100">
            <img src={logoIcon} alt="" className="h-2.5 w-2.5" aria-hidden="true" />
          </div>
          <span className="text-[10px] font-medium text-stone-400">Arxivian</span>
        </div>
        <div className="pl-5 leading-relaxed text-stone-600">
          <strong className="text-stone-800">RLHF</strong> fine-tunes language models using human
          preference rankings to better align outputs with user intent.
        </div>
      </div>
    </div>
  )
}

export function PaperLibraryIllustration() {
  return (
    <div className="relative h-24">
      {[
        { id: '2312.00752', title: 'LLM Alignment Survey', opacity: 0.7, offset: 16 },
        { id: '2310.06825', title: 'Scaling Laws for LMs', opacity: 0.85, offset: 8 },
        { id: '2306.15595', title: 'Direct Preference Optimization', opacity: 1, offset: 0 },
      ].map((paper) => (
        <div
          key={paper.id}
          className="absolute right-0 left-0 flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2"
          style={{ opacity: paper.opacity, top: paper.offset }}
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-stone-400" strokeWidth={1.5} />
          <span className="font-mono text-[10px] text-stone-400">{paper.id}</span>
          <span className="truncate text-xs text-stone-600">{paper.title}</span>
        </div>
      ))}
    </div>
  )
}

export function SmartSearchIllustration() {
  return (
    <div className="space-y-2">
      {/* Retrieval pipeline */}
      <div className="flex items-center gap-1.5 text-[10px] text-stone-400">
        <Search className="h-3 w-3" strokeWidth={1.5} />
        <span>vector + full-text retrieval</span>
      </div>
      {/* Retrieved chunks */}
      <div className="space-y-1.5 text-[11px] leading-relaxed text-stone-500">
        <div className="flex items-center gap-2 rounded border border-stone-100 bg-white px-2.5 py-1.5">
          <span className="shrink-0 text-[10px] font-medium text-amber-700">0.94</span>
          <span className="truncate">
            ...self-attention mechanism allows the model to attend...
          </span>
        </div>
        <div className="flex items-center gap-2 rounded border border-stone-100 bg-white px-2.5 py-1.5">
          <span className="shrink-0 text-[10px] font-medium text-amber-700">0.87</span>
          <span className="truncate">
            ...multi-head attention projects queries, keys, and values...
          </span>
        </div>
      </div>
    </div>
  )
}

export function CitationExplorerIllustration() {
  return (
    <div className="overflow-hidden rounded-lg border border-stone-200 bg-stone-50/80">
      {/* Root paper header */}
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-amber-50">
          <GitBranch className="h-3 w-3 text-amber-600" strokeWidth={1.5} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-stone-400">1706.03762</span>
            <span className="text-[10px] text-stone-400">3 references</span>
          </div>
          <p className="truncate text-[11px] leading-snug text-stone-700">
            Attention Is All You Need
          </p>
        </div>
        <ChevronDown className="h-3 w-3 shrink-0 text-stone-300" strokeWidth={1.5} />
      </div>
      {/* Citation branches */}
      <div className="px-3 pb-2.5">
        <div className="ml-8 space-y-1 border-l-2 border-stone-200 pl-2.5">
          {[
            { num: 1, title: 'Neural Machine Translation by Jointly...', year: '2014' },
            { num: 2, title: 'Sequence to Sequence Learning with...', year: '2014' },
            { num: 3, title: 'Effective Approaches to Attention-based...', year: '2015' },
          ].map((ref) => (
            <div key={ref.num} className="flex items-center gap-1.5 text-[11px] text-stone-500">
              <span className="font-mono text-[10px] text-stone-400">{ref.num}.</span>
              <span className="truncate">{ref.title}</span>
              <span className="shrink-0 font-mono text-[10px] text-stone-300">{ref.year}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

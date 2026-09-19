import { EVIDENCE_KIND_LABELS } from '../../lib/scoring'
import type { EvidenceSpan } from '../../types/api'

interface EvidenceListProps {
  evidence: EvidenceSpan[]
}

/** Quoted spans grouped by kind; pseudocode keeps its whitespace in a code block. */
export default function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return <p className="text-sm text-stone-400">No evidence quoted for this dimension.</p>
  }

  const groups = new Map<string, EvidenceSpan[]>()
  for (const span of evidence) {
    const list = groups.get(span.kind) ?? []
    list.push(span)
    groups.set(span.kind, list)
  }

  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([kind, spans]) => (
        <section key={kind}>
          <h4 className="text-xs font-medium uppercase tracking-wide text-stone-500 mb-2">
            {EVIDENCE_KIND_LABELS[kind] ?? kind}
          </h4>
          <div className="space-y-2">
            {spans.map((span, i) =>
              kind === 'pseudocode' ? (
                <pre
                  key={i}
                  className="font-mono text-xs bg-stone-50 border border-stone-200 rounded-lg p-3 whitespace-pre-wrap text-stone-700"
                >
                  {span.text}
                </pre>
              ) : (
                <blockquote
                  key={i}
                  className="border-l-2 border-amber-700/40 pl-3 text-sm text-stone-600 leading-relaxed"
                >
                  {span.text}
                  {span.source && (
                    <span className="block mt-1 text-xs text-stone-400 font-mono">{span.source}</span>
                  )}
                </blockquote>
              ),
            )}
          </div>
        </section>
      ))}
    </div>
  )
}

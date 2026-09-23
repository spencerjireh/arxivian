// Paper detail: quoted evidence spans for a dimension.
import { EVIDENCE_KIND_LABELS } from '@/lib/scoring'
import type { EvidenceSpan } from '@/types/api'

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
          <h4 className="mb-2 text-xs font-medium tracking-wide text-stone-500 uppercase">
            {EVIDENCE_KIND_LABELS[kind] ?? kind}
          </h4>
          <div className="space-y-2">
            {spans.map((span, i) =>
              kind === 'pseudocode' ? (
                <pre
                  key={i}
                  className="rounded-lg border border-stone-200 bg-stone-50 p-3 font-mono text-xs whitespace-pre-wrap text-stone-700"
                >
                  {span.text}
                </pre>
              ) : (
                <blockquote
                  key={i}
                  className="border-l-2 border-amber-700/40 pl-3 text-sm leading-relaxed text-stone-600"
                >
                  {span.text}
                  {span.source && (
                    <span className="mt-1 block font-mono text-xs text-stone-400">
                      {span.source}
                    </span>
                  )}
                </blockquote>
              )
            )}
          </div>
        </section>
      ))}
    </div>
  )
}

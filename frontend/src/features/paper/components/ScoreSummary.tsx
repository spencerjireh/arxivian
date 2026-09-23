// Paper detail: headline, meta line and the dimension meter on top of the breakdown.
import { Zap } from 'lucide-react'
import DimensionMeter from '@/components/ui/DimensionMeter'
import Chip from '@/components/ui/Chip'
import type { PaperScoreDetail } from '@/types/api'

interface ScoreSummaryProps {
  detail: PaperScoreDetail
}

export default function ScoreSummary({ detail }: ScoreSummaryProps) {
  const { headline, meta, compute_match, scores } = detail
  return (
    <div className="space-y-3">
      <p className="font-display text-2xl leading-snug text-stone-900">{headline}</p>
      {(meta.length > 0 || compute_match === true) && (
        <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-stone-500">
          {meta.length > 0 && <span>{meta.join(' · ')}</span>}
          {compute_match === true && (
            <Chip tone="accent" size="md" icon={<Zap className="h-3 w-3" strokeWidth={1.5} />}>
              Fits your compute
            </Chip>
          )}
        </p>
      )}
      <DimensionMeter scores={scores} size="md" className="max-w-xl" />
    </div>
  )
}

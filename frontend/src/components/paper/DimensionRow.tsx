import { useState } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import Chip from '../ui/Chip'
import { AnimatedCollapse } from '../ui/AnimatedCollapse'
import DistributionBar from './DistributionBar'
import EvidenceList from './EvidenceList'
import JudgmentList from './JudgmentList'
import { DIMENSION_LABELS, LEVEL_LABELS, isLowConfidence } from '../../lib/scoring'
import type { DimensionDetail } from '../../types/api'

interface DimensionRowProps {
  dimension: DimensionDetail
  defaultOpen?: boolean
}

const bandTone = { LOW: 'neutral', MED: 'accent', HIGH: 'success' } as const

/** One rubric dimension: band, score, confidence, level distribution, and its evidence. */
export default function DimensionRow({ dimension, defaultOpen = false }: DimensionRowProps) {
  const [open, setOpen] = useState(defaultOpen)
  const low = isLowConfidence(dimension.confidence)
  const labels = LEVEL_LABELS[dimension.dimension]
  const panelId = `dimension-${dimension.dimension}`

  return (
    <div className="rounded-xl border border-stone-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full flex-col gap-3 px-5 py-4 text-left"
      >
        <div className="flex items-center gap-3">
          <span className="font-display flex-1 text-lg text-stone-900">
            {DIMENSION_LABELS[dimension.dimension]}
          </span>
          <Chip tone={bandTone[dimension.band]} size="md">
            {dimension.band}
          </Chip>
          <span className="font-mono text-sm text-stone-700 tabular-nums">
            {dimension.score}/100
          </span>
          <span className="font-mono text-xs text-stone-400 tabular-nums">
            {Math.round(dimension.confidence * 100)}% conf.
          </span>
          {low && (
            <Chip
              tone="warning"
              size="sm"
              icon={<AlertCircle className="h-3 w-3" strokeWidth={1.5} />}
            >
              Low confidence
            </Chip>
          )}
          <ChevronDown
            className={clsx('h-4 w-4 text-stone-400 transition-transform', open && 'rotate-180')}
            strokeWidth={1.5}
          />
        </div>
        <div className="flex items-center gap-3">
          <DistributionBar
            probabilities={dimension.probabilities}
            level={dimension.level}
            maxLevel={dimension.max_level}
            labels={labels}
            className="flex-1"
          />
          <span className="text-xs whitespace-nowrap text-stone-500">
            {labels?.[dimension.level] ?? `Level ${dimension.level}`}
          </span>
        </div>
      </button>
      <AnimatedCollapse isOpen={open}>
        <div id={panelId} className="space-y-5 border-t border-stone-100 px-5 pt-4 pb-5">
          {dimension.reasoning && <p className="text-sm text-stone-600">{dimension.reasoning}</p>}
          <JudgmentList judgments={dimension.judgments} />
          <EvidenceList evidence={dimension.evidence} />
        </div>
      </AnimatedCollapse>
    </div>
  )
}

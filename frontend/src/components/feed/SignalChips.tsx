import { Code2, Cpu, Database, GitBranch, Zap } from 'lucide-react'
import Chip from '../ui/Chip'
import type { FeedSignals } from '../../types/api'

interface SignalChipsProps {
  signals: FeedSignals
  size?: 'sm' | 'md'
}

/**
 * Only truthy signals render. There is deliberately no negative chip: "no code" is a
 * v1.1 claim that needs the code-gap search behind it (feed-prd section 1).
 */
export default function SignalChips({ signals, size = 'sm' }: SignalChipsProps) {
  const iconClass = 'w-3 h-3'
  const chips: {
    key: string
    label: string
    icon: React.ReactNode
    tone: 'neutral' | 'success' | 'accent'
  }[] = []

  if (signals.pseudocode_present) {
    chips.push({
      key: 'pseudocode',
      label: 'Pseudocode present',
      icon: <Code2 className={iconClass} strokeWidth={1.5} />,
      tone: 'neutral',
    })
  }
  if (signals.public_datasets) {
    chips.push({
      key: 'datasets',
      label: 'Public datasets',
      icon: <Database className={iconClass} strokeWidth={1.5} />,
      tone: 'neutral',
    })
  }
  if (signals.single_gpu) {
    chips.push({
      key: 'gpu',
      label: '1 GPU',
      icon: <Cpu className={iconClass} strokeWidth={1.5} />,
      tone: 'neutral',
    })
  }
  if (signals.code_released) {
    chips.push({
      key: 'code',
      label: 'Code released',
      icon: <GitBranch className={iconClass} strokeWidth={1.5} />,
      tone: 'success',
    })
  }
  if (signals.compute_match === true) {
    chips.push({
      key: 'fits',
      label: 'Fits your compute',
      icon: <Zap className={iconClass} strokeWidth={1.5} />,
      tone: 'accent',
    })
  }

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {chips.map((chip) => (
        <Chip key={chip.key} tone={chip.tone} size={size} icon={chip.icon}>
          {chip.label}
        </Chip>
      ))}
    </div>
  )
}

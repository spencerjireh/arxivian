import { GitBranch, Layers, Target } from 'lucide-react'
import Chip from '../ui/Chip'
import { formatAnswer } from '../../lib/scoring'
import type { PaperAttributes } from '../../types/api'

interface AttributeChipsProps {
  attributes: PaperAttributes
}

/** Task type, model family, and the authors' code-release statement (never a "no code" chip). */
export default function AttributeChips({ attributes }: AttributeChipsProps) {
  const { task_type, model_family, code_released } = attributes
  const iconClass = 'w-3 h-3'
  const chips: React.ReactNode[] = []

  if (task_type && task_type.answer !== 'other') {
    chips.push(
      <Chip key="task" size="md" icon={<Target className={iconClass} strokeWidth={1.5} />} title={`${Math.round(task_type.confidence * 100)}% confidence`}>
        {formatAnswer(task_type.answer)}
      </Chip>,
    )
  }
  if (model_family && model_family.answer !== 'other') {
    chips.push(
      <Chip key="family" size="md" icon={<Layers className={iconClass} strokeWidth={1.5} />} title={`${Math.round(model_family.confidence * 100)}% confidence`}>
        {formatAnswer(model_family.answer)}
      </Chip>,
    )
  }
  if (code_released && code_released.answer === true) {
    chips.push(
      <Chip key="code" size="md" tone="success" icon={<GitBranch className={iconClass} strokeWidth={1.5} />} title="Stated by the authors">
        Code released
      </Chip>,
    )
  }

  if (chips.length === 0) return null
  return <div className="flex flex-wrap gap-2">{chips}</div>
}

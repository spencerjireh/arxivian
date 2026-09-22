// Feed: digest week picker over the available_weeks list.
import { ChevronLeft, ChevronRight } from 'lucide-react'
import Button from '@/components/ui/Button'
import { selectClass } from '@/lib/formClasses'
import { formatWeek } from '../lib/feedParams'
import type { AvailableWeek } from '@/types/api'

interface WeekSelectorProps {
  weeks: AvailableWeek[]
  value: string
  onChange: (week: string) => void
}

/** Past digests are cached, so browsing weeks is free. Newest first. */
export default function WeekSelector({ weeks, value, onChange }: WeekSelectorProps) {
  const sorted = [...weeks].sort((a, b) => (a.week_start < b.week_start ? 1 : -1))
  const index = sorted.findIndex((w) => w.week_start === value)
  const newer = index > 0 ? sorted[index - 1] : undefined
  const older = index >= 0 && index < sorted.length - 1 ? sorted[index + 1] : undefined

  return (
    <div className="inline-flex items-center gap-1">
      <Button
        variant="icon"
        size="sm"
        aria-label="Older week"
        disabled={!older}
        onClick={() => older && onChange(older.week_start)}
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={1.5} />
      </Button>
      <select
        aria-label="Digest week"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={selectClass}
      >
        {sorted.map((w) => (
          <option key={w.week_start} value={w.week_start}>
            Week of {formatWeek(w.week_start)} ({w.paper_count} paper
            {w.paper_count !== 1 ? 's' : ''})
          </option>
        ))}
      </select>
      <Button
        variant="icon"
        size="sm"
        aria-label="Newer week"
        disabled={!newer}
        onClick={() => newer && onChange(newer.week_start)}
      >
        <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
      </Button>
    </div>
  )
}

import { useState } from 'react'
import { X } from 'lucide-react'
import Input from '../ui/Input'
import Chip from '../ui/Chip'
import { MAX_KEYWORDS, MAX_KEYWORD_LENGTH } from '../../lib/arxivCategories'

interface KeywordInputProps {
  value: string[]
  onChange: (value: string[]) => void
}

/** Enter or comma adds a keyword; duplicates (case-insensitive) are dropped. */
export default function KeywordInput({ value, onChange }: KeywordInputProps) {
  const [draft, setDraft] = useState('')

  const add = (raw: string) => {
    const next = raw.trim().toLowerCase().slice(0, MAX_KEYWORD_LENGTH)
    if (!next || value.includes(next) || value.length >= MAX_KEYWORDS) return
    onChange([...value, next])
  }

  return (
    <div>
      <Input
        value={draft}
        placeholder={
          value.length >= MAX_KEYWORDS ? 'Keyword limit reached' : 'Add a keyword and press Enter'
        }
        disabled={value.length >= MAX_KEYWORDS}
        aria-label="Interest keyword"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault()
            add(draft)
            setDraft('')
          }
        }}
        onBlur={() => {
          if (draft.trim()) {
            add(draft)
            setDraft('')
          }
        }}
      />
      {value.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {value.map((k) => (
            <Chip key={k} size="md">
              {k}
              <button
                type="button"
                aria-label={`Remove ${k}`}
                onClick={() => onChange(value.filter((v) => v !== k))}
                className="ml-0.5 rounded hover:bg-stone-200"
              >
                <X className="h-3 w-3" strokeWidth={1.5} />
              </button>
            </Chip>
          ))}
        </div>
      )}
    </div>
  )
}

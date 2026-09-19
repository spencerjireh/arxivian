import { useState } from 'react'
import Button from '../ui/Button'
import CategoryPicker from './CategoryPicker'
import ComputeProfilePicker from './ComputeProfilePicker'
import KeywordInput from './KeywordInput'
import type { ComputeProfile, FeedProfileInput } from '../../types/api'

export interface FeedProfileInitial {
  categories?: string[]
  compute_profile?: ComputeProfile | null
  keywords?: string[]
}

interface FeedProfileFormProps {
  initialValue?: FeedProfileInitial | null
  onSubmit: (profile: FeedProfileInput) => void
  isSubmitting: boolean
  submitLabel: string
}

interface FormErrors {
  categories?: string
  compute_profile?: string
}

/** Pure form: local state, validation on submit, no store access. */
export default function FeedProfileForm({ initialValue, onSubmit, isSubmitting, submitLabel }: FeedProfileFormProps) {
  const [categories, setCategories] = useState<string[]>(initialValue?.categories ?? [])
  const [computeProfile, setComputeProfile] = useState<ComputeProfile | undefined>(
    initialValue?.compute_profile ?? undefined,
  )
  const [keywords, setKeywords] = useState<string[]>(initialValue?.keywords ?? [])
  const [errors, setErrors] = useState<FormErrors>({})
  const [attempted, setAttempted] = useState(false)

  const validate = (): FormErrors => ({
    ...(categories.length === 0 ? { categories: 'Pick at least one category' } : {}),
    ...(computeProfile ? {} : { compute_profile: 'Choose your compute setup' }),
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setAttempted(true)
    const next = validate()
    setErrors(next)
    if (Object.keys(next).length > 0 || !computeProfile) return
    onSubmit({ categories, compute_profile: computeProfile, keywords })
  }

  const update = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v)
    if (attempted) setErrors({})
  }

  return (
    <form onSubmit={submit} className="space-y-8" noValidate>
      <section>
        <h2 className="font-display text-lg text-stone-900 mb-1">Categories</h2>
        <p className="text-sm text-stone-500 mb-3">Which arXiv listings should the weekly digest draw from?</p>
        <CategoryPicker value={categories} onChange={update(setCategories)} error={attempted ? errors.categories : undefined} />
      </section>

      <section>
        <h2 className="font-display text-lg text-stone-900 mb-1">Compute</h2>
        <p className="text-sm text-stone-500 mb-3">Papers that fit your hardware rank first.</p>
        <ComputeProfilePicker value={computeProfile} onChange={update(setComputeProfile)} error={attempted ? errors.compute_profile : undefined} />
      </section>

      <section>
        <h2 className="font-display text-lg text-stone-900 mb-1">Keywords <span className="text-sm font-body text-stone-400">(optional)</span></h2>
        <p className="text-sm text-stone-500 mb-3">Topics you care about break ties in the ranking.</p>
        <KeywordInput value={keywords} onChange={setKeywords} />
      </section>

      <div className="flex justify-end">
        <Button type="submit" variant="primary" size="lg" isLoading={isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

import { useState } from 'react'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { usePreferences, useAddArxivSearch, useDeleteArxivSearch } from '../../api/preferences'
import { AnimatedCollapse } from '../../components/ui/AnimatedCollapse'
import Button from '../../components/ui/Button'
import type { ArxivSearchConfig } from '../../types/api'

const inputClass =
  'w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150'
const labelClass = 'block text-xs text-stone-500 mb-1.5'

export default function ArxivSearchesSection() {
  const { data: prefs, isLoading, error: prefsError } = usePreferences()
  const addSearch = useAddArxivSearch()
  const deleteSearch = useDeleteArxivSearch()

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [query, setQuery] = useState('')
  const [categories, setCategories] = useState('')
  const [maxResults, setMaxResults] = useState(10)
  const [addError, setAddError] = useState<string | null>(null)

  const searches = prefs?.arxiv_searches ?? []
  const nameExists = searches.some((s) => s.name.toLowerCase() === name.trim().toLowerCase())

  const handleSave = () => {
    if (nameExists) return

    const config: ArxivSearchConfig = {
      name: name.trim(),
      query: query.trim(),
      max_results: maxResults,
    }
    const cats = categories
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean)
    if (cats.length > 0) config.categories = cats

    setAddError(null)
    addSearch.mutate(config, {
      onSuccess: () => {
        setAddError(null)
        setShowForm(false)
        setName('')
        setQuery('')
        setCategories('')
        setMaxResults(10)
      },
      onError: (err) => {
        const message = err instanceof Error ? err.message : 'Failed to save search'
        setAddError(message)
      },
    })
  }

  const handleDelete = (searchName: string) => {
    deleteSearch.mutate(searchName)
  }

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-lg font-semibold text-stone-900">Saved arXiv Searches</h2>
        {!showForm && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowForm(true)}
            leftIcon={<Plus className="w-3.5 h-3.5" strokeWidth={2} />}
          >
            Add search
          </Button>
        )}
      </div>

      <AnimatedCollapse isOpen={showForm}>
        <div className="border border-stone-200 rounded-lg p-4 mb-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <input
                type="text"
                placeholder="Search name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={clsx(inputClass, nameExists && 'border-red-300 focus:border-red-500')}
              />
              {nameExists && (
                <p className="mt-1 text-xs text-red-600">A search with this name already exists</p>
              )}
            </div>
            <input
              type="text"
              placeholder="Query (e.g. transformer attention)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={inputClass}
            />
            <input
              type="text"
              placeholder="Categories (comma-separated)"
              value={categories}
              onChange={(e) => setCategories(e.target.value)}
              className={inputClass}
            />
            <div>
              <label className={labelClass}>Max results (1-50)</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                className={inputClass}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleSave}
              disabled={!name.trim() || !query.trim() || nameExists || addSearch.isPending}
              isLoading={addSearch.isPending}
            >
              Save
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowForm(false)}
              disabled={addSearch.isPending}
            >
              Cancel
            </Button>
          </div>
          {addError && (
            <p className="text-xs text-red-600">{addError}</p>
          )}
        </div>
      </AnimatedCollapse>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-stone-300" strokeWidth={1.5} />
        </div>
      ) : prefsError ? (
        <p className="text-sm text-stone-500 py-4">Unable to load saved searches</p>
      ) : searches.length === 0 ? (
        <p className="text-sm text-stone-400 py-4">No saved searches</p>
      ) : (
        <div className="space-y-2">
          {searches.map((search) => (
            <ArxivSearchRow
              key={search.name}
              search={search}
              onDelete={handleDelete}
              isDeleting={deleteSearch.isPending && deleteSearch.variables === search.name}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface ArxivSearchRowProps {
  search: ArxivSearchConfig
  onDelete: (name: string) => void
  isDeleting: boolean
}

function ArxivSearchRow({ search, onDelete, isDeleting }: ArxivSearchRowProps) {
  return (
    <div className="group flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-stone-50 transition-colors">
      <span
        className={clsx(
          'w-2 h-2 rounded-full flex-shrink-0',
          search.enabled !== false ? 'bg-emerald-400' : 'bg-stone-300'
        )}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-stone-900">{search.name}</span>
          <span className="text-xs text-stone-400 truncate">{search.query}</span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          {search.categories?.map((cat) => (
            <span
              key={cat}
              className="text-xs px-1.5 py-0.5 bg-stone-100 text-stone-500 rounded"
            >
              {cat}
            </span>
          ))}
          {search.max_results && (
            <span className="text-xs text-stone-400 font-mono">
              max: {search.max_results}
            </span>
          )}
        </div>
      </div>
      <button
        onClick={() => onDelete(search.name)}
        disabled={isDeleting}
        className={clsx(
          'p-1.5 rounded-md opacity-0 group-hover:opacity-100',
          'text-stone-400 hover:text-red-600 hover:bg-red-50',
          'transition-all duration-150 disabled:opacity-50',
          'flex-shrink-0'
        )}
        aria-label="Delete search"
      >
        {isDeleting ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
        ) : (
          <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
        )}
      </button>
    </div>
  )
}

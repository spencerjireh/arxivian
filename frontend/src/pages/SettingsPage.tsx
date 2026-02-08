import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser, useClerk } from '@clerk/clerk-react'
import { RotateCcw, Plus, Trash2, LogOut, Loader2 } from 'lucide-react'
import { useSettingsStore } from '../stores/settingsStore'
import { usePreferences, useAddArxivSearch, useDeleteArxivSearch } from '../api/preferences'
import { AnimatedCollapse } from '../components/ui/AnimatedCollapse'
import Button from '../components/ui/Button'
import type { LLMProvider, ArxivSearchConfig } from '../types/api'

const inputClass =
  'w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150'
const labelClass = 'block text-xs text-stone-500 mb-1.5'

export default function SettingsPage() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <h1 className="font-display text-2xl font-semibold text-stone-900">Settings</h1>
        <AccountSection />
        <LLMPreferencesSection />
        <ArxivSearchesSection />
      </div>
    </div>
  )
}

// -- Account Section --

function AccountSection() {
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  if (!user) return null

  const handleSignOut = async () => {
    await signOut()
    navigate('/sign-in')
  }

  const handleDeleteAccount = async () => {
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await user.delete()
      navigate('/sign-in')
    } catch (err) {
      setIsDeleting(false)
      const message = err instanceof Error ? err.message : 'Failed to delete account'
      setDeleteError(message)
    }
  }

  const displayName = user.fullName || 'User'
  const email = user.primaryEmailAddress?.emailAddress || ''
  const joinedDate = user.createdAt
    ? new Date(user.createdAt).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : ''

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6">
      <h2 className="font-display text-lg font-semibold text-stone-900 mb-4">Account</h2>

      <div className="flex items-center gap-4 mb-6">
        <img
          src={user.imageUrl}
          alt=""
          className="w-12 h-12 rounded-full ring-2 ring-stone-200"
        />
        <div>
          <p className="text-sm font-medium text-stone-900">{displayName}</p>
          <p className="text-sm text-stone-500">{email}</p>
          {joinedDate && (
            <p className="text-xs text-stone-400 mt-0.5">Joined {joinedDate}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleSignOut}
          leftIcon={<LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />}
        >
          Sign out
        </Button>

        {showDeleteConfirm ? (
          <div className="flex items-center gap-2">
            <p className="text-xs text-stone-500">Delete your account? This cannot be undone.</p>
            {deleteError && <p className="text-xs text-red-600">{deleteError}</p>}
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteAccount}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Confirm delete'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowDeleteConfirm(false)
                setDeleteError(null)
              }}
              disabled={isDeleting}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowDeleteConfirm(true)}
            leftIcon={<Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />}
          >
            Delete account
          </Button>
        )}
      </div>
    </div>
  )
}

// -- LLM Preferences Section --

function LLMPreferencesSection() {
  const {
    provider,
    model,
    temperature,
    top_k,
    guardrail_threshold,
    max_retrieval_attempts,
    conversation_window,
    setProvider,
    setModel,
    setTemperature,
    setTopK,
    setGuardrailThreshold,
    setMaxRetrievalAttempts,
    setConversationWindow,
    resetToDefaults,
  } = useSettingsStore()

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-display text-lg font-semibold text-stone-900">LLM Preferences</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={resetToDefaults}
          leftIcon={<RotateCcw className="w-3.5 h-3.5" strokeWidth={1.5} />}
        >
          Reset to defaults
        </Button>
      </div>
      <p className="text-xs text-stone-400 mb-4">Stored in this browser only</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        <div>
          <label className={labelClass}>Provider</label>
          <select
            value={provider || ''}
            onChange={(e) => setProvider((e.target.value || undefined) as LLMProvider | undefined)}
            className={inputClass}
          >
            <option value="">Default</option>
            <option value="openai">OpenAI</option>
            <option value="nvidia_nim">NVIDIA NIM</option>
          </select>
        </div>

        <div>
          <label className={labelClass}>Model</label>
          <input
            type="text"
            value={model || ''}
            onChange={(e) => setModel(e.target.value || undefined)}
            placeholder="Default model"
            className={inputClass}
          />
        </div>

        <div>
          <label className={labelClass}>
            Temperature
            <span className="float-right font-mono text-stone-400">{temperature}</span>
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>

        <div>
          <label className={labelClass}>
            Top K
            <span className="float-right font-mono text-stone-400">{top_k}</span>
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={top_k}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>

        <div>
          <label className={labelClass}>
            Guardrail Threshold
            <span className="float-right font-mono text-stone-400">{guardrail_threshold}</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={guardrail_threshold}
            onChange={(e) => setGuardrailThreshold(Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>

        <div>
          <label className={labelClass}>
            Max Retrieval
            <span className="float-right font-mono text-stone-400">{max_retrieval_attempts}</span>
          </label>
          <input
            type="range"
            min={1}
            max={5}
            step={1}
            value={max_retrieval_attempts}
            onChange={(e) => setMaxRetrievalAttempts(Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>

        <div>
          <label className={labelClass}>
            Context Window
            <span className="float-right font-mono text-stone-400">{conversation_window}</span>
          </label>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            value={conversation_window}
            onChange={(e) => setConversationWindow(Number(e.target.value))}
            className="w-full accent-stone-700"
          />
        </div>
      </div>
    </div>
  )
}

// -- Saved arXiv Searches Section --

function ArxivSearchesSection() {
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
                className={`${inputClass} ${nameExists ? '!border-red-300 !focus:border-red-500' : ''}`}
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
        className={`w-2 h-2 rounded-full flex-shrink-0 ${
          search.enabled !== false ? 'bg-emerald-400' : 'bg-stone-300'
        }`}
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
        className="
          p-1.5 rounded-md opacity-0 group-hover:opacity-100
          text-stone-400 hover:text-red-600 hover:bg-red-50
          transition-all duration-150 disabled:opacity-50
          flex-shrink-0
        "
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

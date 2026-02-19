import { RotateCcw } from 'lucide-react'
import { useSettingsStore } from '../stores/settingsStore'
import { useUserStore } from '../stores/userStore'
import Button from '../components/ui/Button'
import type { LLMProvider } from '../types/api'
import AccountSection from './settings/AccountSection'

const inputClass =
  'w-full px-3 py-2 text-sm text-stone-800 bg-white border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-stone-200 focus:border-stone-300 transition-colors duration-150'
const labelClass = 'block text-xs text-stone-500 mb-1.5'
const checkboxClass = 'mt-0.5 accent-stone-700'

export default function SettingsPage() {
  const canAdjustSettings = useUserStore((s) => s.me?.can_adjust_settings ?? false)

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <h1 className="font-display text-2xl font-semibold text-stone-900">Settings</h1>
        <AccountSection />
        <DisplayPreferencesSection />
        {canAdjustSettings && <LLMPreferencesSection />}
      </div>
    </div>
  )
}

function DisplayPreferencesSection() {
  const showInternalSteps = useSettingsStore((s) => s.showInternalSteps)
  const setShowInternalSteps = useSettingsStore((s) => s.setShowInternalSteps)

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6">
      <h2 className="font-display text-lg font-semibold text-stone-900 mb-1">Display</h2>
      <p className="text-xs text-stone-400 mb-4">Control how agent responses are presented</p>

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={showInternalSteps}
          onChange={(e) => setShowInternalSteps(e.target.checked)}
          className={checkboxClass}
        />
        <div>
          <span className="text-sm text-stone-700">Show internal pipeline steps</span>
          <p className="text-xs text-stone-400 mt-0.5">
            Display internal processing steps (guardrail, routing, grading) in the reasoning timeline
          </p>
        </div>
      </label>
    </div>
  )
}

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

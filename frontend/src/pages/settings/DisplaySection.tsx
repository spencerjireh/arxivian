import { useSettingsStore } from '../../stores/settingsStore'

export default function DisplaySection() {
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
          className="mt-0.5 accent-stone-700"
        />
        <div>
          <span className="text-sm text-stone-700">Show internal steps</span>
          <p className="text-xs text-stone-400 mt-0.5">
            Display all pipeline steps (guardrail, routing, grading) during streaming instead of
            only user-facing steps
          </p>
        </div>
      </label>
    </div>
  )
}

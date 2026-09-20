import AccountSection from './settings/AccountSection'
import FeedProfileSection from './settings/FeedProfileSection'

export default function SettingsPage() {
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <h1 className="font-display text-2xl font-semibold text-stone-900">Settings</h1>
        <AccountSection />
        <FeedProfileSection />
      </div>
    </div>
  )
}

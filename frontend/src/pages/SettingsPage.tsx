// /settings route: account and feed profile sections.
import AccountSection from '../components/settings/AccountSection'
import FeedProfileSection from '../components/settings/FeedProfileSection'

export default function SettingsPage() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-6 py-10">
      <h1 className="font-display text-3xl font-semibold text-stone-900">Settings</h1>
      <AccountSection />
      <FeedProfileSection />
    </div>
  )
}

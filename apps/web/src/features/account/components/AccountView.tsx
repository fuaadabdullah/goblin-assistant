import AccountProfileForm from './AccountProfileForm';
import AccountPreferences from './AccountPreferences';
import AccountBillingCard from './AccountBillingCard';
import type { AccountState } from '../hooks/useAccountProfile';
import Seo from '../../../components/Seo';

interface AccountViewProps {
  /** Account state + handlers. */
  state: AccountState;
}

const AccountView = ({ state }: AccountViewProps) => (
  <div className="min-h-screen bg-bg">
    <Seo title="Account" description="Manage your Goblin Assistant account." robots="noindex,nofollow" />
    <main className="max-w-4xl mx-auto p-6 space-y-6" id="main-content" tabIndex={-1}>
      <header>
        <h1 className="text-3xl font-semibold text-text">Account</h1>
        <p className="text-sm text-muted">
          Manage your profile, billing, and preferences in one place.
        </p>
      </header>

      <AccountProfileForm
        name={state.name}
        email={state.email}
        saved={state.saved}
        error={state.error}
        saving={state.saving}
        onNameChange={state.setName}
        onSave={state.handleSave}
      />

      <AccountPreferences preferences={state.preferences} onToggle={state.togglePreference} />

      <AccountBillingCard />
    </main>
  </div>
);

export default AccountView;

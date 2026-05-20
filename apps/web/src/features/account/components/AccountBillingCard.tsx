const AccountBillingCard = () => (
  <section className="bg-surface border border-border rounded-2xl p-6 space-y-3">
    <h2 className="text-lg font-semibold text-text">Billing</h2>
    <p className="text-sm text-muted">
      Billing and plan management will appear here when enabled.
    </p>
    <button
      type="button"
      className="px-4 py-2 rounded-lg border border-border text-text hover:bg-surface-hover"
    >
      View Plans
    </button>
  </section>
);

export default AccountBillingCard;

import type { FC } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useAccountProfile } from './hooks/useAccountProfile';
import AccountView from './components/AccountView';

const AccountScreen: FC = () => {
  const user = useAuthStore(state => state.user);
  const state = useAccountProfile(user);

  return <AccountView state={state} />;
};

export default AccountScreen;

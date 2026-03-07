import type { FC } from 'react';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { useAccountProfile } from './hooks/useAccountProfile';
import AccountView from './components/AccountView';

const AccountScreen: FC = () => {
  const { user } = useAuthSession();
  const state = useAccountProfile(user);

  return <AccountView state={state} />;
};

export default AccountScreen;

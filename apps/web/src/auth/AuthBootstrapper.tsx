import { useAuthSession } from '../hooks/api/useAuthSession';

const AuthBootstrapper = () => {
  // Trigger session bootstrap/validation through React Query.
  useAuthSession();
  return null;
};

export default AuthBootstrapper;

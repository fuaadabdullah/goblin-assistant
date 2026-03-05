import LoginPage, { getServerSideProps } from '../screens/LoginPage';

export { getServerSideProps };

export default function RegisterPage() {
  return <LoginPage initialMode="register" />;
}

import { Bot } from 'lucide-react';
import { BRAND_NAME } from '../../content/brand';

interface LoginHeaderProps {
  isRegister: boolean;
}

export default function LoginHeader({ isRegister }: LoginHeaderProps) {
  return (
    <div className="text-center mb-8">
      <div className="flex items-center justify-center mb-4">
        <Bot className="w-12 h-12 text-primary" />
      </div>
      <h1 className="text-4xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary via-accent to-primary mb-3">
        {BRAND_NAME}
      </h1>
      <h2 className="text-2xl font-bold text-text mb-2">
        {isRegister ? 'Create Account' : 'Welcome Back'}
      </h2>
      <p className="text-muted">
        {isRegister
          ? 'Create an account to save your Goblin Memory and keep your threads organized.'
          : 'Sign in to access your Goblin Memory and pick up where you left off.'}
      </p>
    </div>
  );
}

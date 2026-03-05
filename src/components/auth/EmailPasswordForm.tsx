import { useState, FormEvent } from 'react';

interface EmailPasswordFormProps {
  // eslint-disable-next-line no-unused-vars
  onSubmit: (email: string, password: string) => Promise<void>;
  isRegister: boolean;
  isLoading: boolean;
}

export default function EmailPasswordForm({
  onSubmit,
  isRegister,
  isLoading,
}: EmailPasswordFormProps) {
  const [emailValue, setEmailValue] = useState('');
  const [passwordValue, setPasswordValue] = useState('');
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const emailErrorId = 'email-error';
  const passwordErrorId = 'password-error';
  const passwordHintId = 'password-hint';

  const validateEmail = (emailInput: string) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(emailInput);
  };

  const validatePassword = (passwordInput: string) => {
    if (isRegister) {
      return passwordInput.length >= 8;
    }
    return passwordInput.length > 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    const newErrors: { email?: string; password?: string } = {};

    if (!validateEmail(emailValue)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!validatePassword(passwordValue)) {
      newErrors.password = isRegister
        ? 'Password must be at least 8 characters'
        : 'Password is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    await onSubmit(emailValue, passwordValue);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-muted mb-2">
          Email Address
        </label>
        <input
          id="email"
          type="email"
          value={emailValue}
          onChange={e => {
            setEmailValue(e.target.value);
            if (errors.email) setErrors({ ...errors, email: undefined });
          }}
          required
          className={`w-full px-4 py-3 border rounded-lg bg-surface-hover text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors ${
            errors.email ? 'border-danger' : 'border-border'
          }`}
          placeholder="you@example.com"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? emailErrorId : undefined}
        />
        {errors.email && (
          <p className="mt-1 text-sm text-danger" id={emailErrorId} role="alert">
            {errors.email}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-muted mb-2">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={passwordValue}
          onChange={e => {
            setPasswordValue(e.target.value);
            if (errors.password) setErrors({ ...errors, password: undefined });
          }}
          required
          className={`w-full px-4 py-3 border rounded-lg bg-surface-hover text-text placeholder-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors ${
            errors.password ? 'border-danger' : 'border-border'
          }`}
          placeholder="••••••••"
          aria-invalid={Boolean(errors.password)}
          aria-describedby={
            errors.password ? passwordErrorId : isRegister ? passwordHintId : undefined
          }
        />
        {errors.password && (
          <p className="mt-1 text-sm text-danger" id={passwordErrorId} role="alert">
            {errors.password}
          </p>
        )}
        {isRegister && !errors.password && (
          <p className="mt-1 text-xs text-muted" id={passwordHintId}>
            Must be at least 8 characters
          </p>
        )}
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full bg-primary hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed text-text-inverse font-semibold py-3 px-4 rounded-lg transition-all duration-200 flex items-center justify-center shadow-glow-primary"
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-text-inverse mr-2"></div>
            Processing...
          </>
        ) : (
          <>{isRegister ? 'Create Account' : 'Sign In'}</>
        )}
      </button>
    </form>
  );
}

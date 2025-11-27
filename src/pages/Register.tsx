import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';

const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { register, loginWithGoogle, registerPasskey } = useAuth();
  const navigate = useNavigate();

  const handleGoogleRegister = async () => {
    setError('');
    setIsLoading(true);

    try {
      await loginWithGoogle();
      navigate('/chat');
    } catch (err) {
      setError('Google registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyRegister = async () => {
    if (!email) {
      setError('Please enter your email first');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      await registerPasskey(email);
      setError('Passkey registered successfully! You can now use it to sign in.');
    } catch (err) {
      setError('Passkey registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    setIsLoading(true);

    try {
      await register(email, password, name);
      navigate('/chat');
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="register-container">
      <Card className="register-card">
        <CardHeader>
          <CardTitle>Create Account</CardTitle>
          <CardDescription>Sign up for Goblin Assistant</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Social Registration Buttons */}
          <div className="social-login">
            <Button
              type="button"
              variant="outline"
              onClick={handleGoogleRegister}
              disabled={isLoading}
              className="google-button"
            >
              <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Sign up with Google
            </Button>
          </div>

          <div className="divider">
            <span>or</span>
          </div>

          <form onSubmit={handleSubmit} className="register-form">
            <div className="form-group">
              <Label htmlFor="name">Full Name</Label>
              <Input
                id="name"
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Enter your full name"
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-group">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                disabled={isLoading}
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="register-button" disabled={isLoading}>
              {isLoading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          {email && (
            <div className="passkey-section">
              <div className="divider">
                <span>or</span>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handlePasskeyRegister}
                disabled={isLoading}
                className="passkey-button"
              >
                🔐 Register Passkey
              </Button>
              <p className="passkey-description">
                Register a passkey for passwordless authentication
              </p>
            </div>
          )}

          <div className="auth-links">
            <p>
              Already have an account?{' '}
              <Link to="/login" className="auth-link">
                Sign in
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Register;

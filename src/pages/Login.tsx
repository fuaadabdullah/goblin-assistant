import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Loader2 } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [authMethod, setAuthMethod] = useState<'email' | 'passkey'>('email');

  const { login, loginWithGoogle } = useAuth();
  const { showError } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/chat');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      showError('Login Failed', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setIsLoading(true);

    try {
      await loginWithGoogle();
      navigate('/chat');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Google authentication failed';
      setError(errorMessage);
      showError('Google Login Failed', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setError('');
    setIsLoading(true);

    try {
      // Get challenge from server
      const challengeResponse = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/passkey/challenge`,
        {
          method: 'POST',
        }
      );

      if (!challengeResponse.ok) {
        throw new Error('Failed to get challenge from server');
      }

      const { challenge } = await challengeResponse.json();

      // Use WebAuthn API
      const credential = (await navigator.credentials.get({
        publicKey: {
          challenge: Uint8Array.from(atob(challenge.replace(/-/g, '+').replace(/_/g, '/')), c =>
            c.charCodeAt(0)
          ),
          allowCredentials: [], // Allow any credential for this user
          userVerification: 'preferred',
        },
      })) as PublicKeyCredential;

      if (credential) {
        // Send credential to server for verification
        const response = await fetch(
          `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/passkey/auth`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: email || 'user@example.com', // In production, get email from credential
              credential_id: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
              authenticator_data: btoa(
                String.fromCharCode(
                  ...new Uint8Array(
                    (credential.response as AuthenticatorAssertionResponse).authenticatorData
                  )
                )
              ),
              client_data_json: btoa(
                String.fromCharCode(
                  ...new Uint8Array(
                    (credential.response as AuthenticatorAssertionResponse).clientDataJSON
                  )
                )
              ),
              signature: btoa(
                String.fromCharCode(
                  ...new Uint8Array(
                    (credential.response as AuthenticatorAssertionResponse).signature
                  )
                )
              ),
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Passkey authentication failed');
        }

        const data = await response.json();
        localStorage.setItem('auth_token', data.access_token);
        window.location.reload();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Passkey authentication failed';
      setError(errorMessage);
      showError('Passkey Login Failed', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-card">
        <CardHeader>
          <div className="flex flex-col items-center space-y-4">
            <img src="/goblinos-goblin.png" alt="GoblinOS" className="h-12 w-12" />
            <div className="text-center">
              <CardTitle>Welcome to Goblin Assistant</CardTitle>
              <CardDescription>Sign in to access your AI assistant</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Social Login Buttons */}
          <div className="social-login">
            <Button
              type="button"
              variant="outline"
              onClick={handleGoogleLogin}
              disabled={isLoading}
              className="google-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
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
                  Continue with Google
                </>
              )}
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={handlePasskeyLogin}
              disabled={isLoading}
              className="passkey-button"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>🔐 Sign in with Passkey</>
              )}
            </Button>
          </div>

          <div className="divider">
            <span>or</span>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
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

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="login-button" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <div className="auth-links">
            <p>
              Don&apos;t have an account?{' '}
              <Link to="/register" className="auth-link">
                Sign up
              </Link>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;

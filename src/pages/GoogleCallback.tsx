import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const GoogleCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      if (error) {
        console.error('OAuth error:', error);
        navigate('/login?error=oauth_failed');
        return;
      }

      if (!code) {
        console.error('No authorization code received');
        navigate('/login?error=no_code');
        return;
      }

      try {
        // Exchange code for token
        const response = await fetch(
          `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/google/callback`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              code: code,
              state: state,
            }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            `Failed to exchange code for token: ${errorData.detail || response.statusText}`
          );
        }

        const data = await response.json();
        const { access_token, user: userInfo } = data;

        // Store token and user data
        localStorage.setItem('auth_token', access_token);
        localStorage.setItem('user_data', JSON.stringify(userInfo));

        // Update auth context by calling checkAuth
        await checkAuth();

        // Navigate to chat
        navigate('/chat');
      } catch (error) {
        console.error('OAuth callback error:', error);
        navigate('/login?error=callback_failed');
      }
    };

    handleCallback();
  }, [searchParams, navigate, checkAuth]);

  return (
    <div className="callback-container">
      <div className="callback-content">
        <h2>Completing sign in...</h2>
        <p>Please wait while we finish signing you in with Google.</p>
        <div className="spinner"></div>
      </div>
    </div>
  );
};

export default GoogleCallback;

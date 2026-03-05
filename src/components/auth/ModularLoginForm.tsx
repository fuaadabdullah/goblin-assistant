// Enhanced ModularLoginForm with Login and Registration

import React, { useState } from 'react';

interface ModularLoginFormProps {
  onSuccess?: () => void;
  onError?: (message: string) => void;
}

export default function ModularLoginForm({ onSuccess, onError }: ModularLoginFormProps = {}) {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    name: ''
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
      const payload = isLogin 
        ? { email: formData.email, password: formData.password }
        : { 
            email: formData.email, 
            password: formData.password, 
            confirmPassword: formData.confirmPassword,
            name: formData.name 
          };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.message || (isLogin ? 'Login failed' : 'Registration failed'));
      }

      const data = await response.json();
      
      if (isLogin) {
        // Handle successful login
        if (data.user) {
          // Store user data in localStorage
          localStorage.setItem('user', JSON.stringify(data.user));

          // Use callback if provided, otherwise redirect to dashboard
          if (onSuccess) {
            onSuccess();
          } else {
            window.location.href = '/dashboard';
          }
        } else {
          throw new Error('Login successful but no user data returned');
        }
      } else {
        // Handle successful registration
        setIsLogin(true);
        setFormData({ email: '', password: '', confirmPassword: '', name: '' });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);

      // Use callback if provided
      if (onError) {
        onError(errorMessage);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="max-w-md mx-auto bg-white p-8 rounded-lg shadow-md">
      {/* Toggle between Login and Register */}
      <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
        <button
          onClick={() => setIsLogin(true)}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
            isLogin
              ? 'bg-white text-indigo-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Login
        </button>
        <button
          onClick={() => setIsLogin(false)}
          className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
            !isLogin
              ? 'bg-white text-indigo-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          Create Account
        </button>
      </div>

      <h2 className="text-2xl font-bold text-center mb-6">
        {isLogin ? 'Welcome Back' : 'Join Us Today'}
      </h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {!isLogin && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input 
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Enter your full name"
              required={!isLogin}
              suppressHydrationWarning
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
          <input 
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter your email"
            required
            suppressHydrationWarning
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {isLogin ? 'Password' : 'Create Password'}
          </label>
          <input 
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder={isLogin ? "Enter your password" : "Create a strong password"}
            minLength={6}
            required
            suppressHydrationWarning
          />
        </div>

        {!isLogin && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
            <input 
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Confirm your password"
              minLength={6}
              required={!isLogin}
              suppressHydrationWarning
            />
          </div>
        )}

        <button 
          type="submit"
          disabled={isLoading}
          className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {isLogin ? 'Logging in...' : 'Creating account...'}
            </span>
          ) : (
            isLogin ? 'Sign In' : 'Create Account'
          )}
        </button>
      </form>

      {/* Additional Links */}
      <div className="mt-6 text-center text-sm text-gray-600">
        {isLogin ? (
          <p>
            Don't have an account?{' '}
            <button
              onClick={() => setIsLogin(false)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Sign up here
            </button>
          </p>
        ) : (
          <p>
            Already have an account?{' '}
            <button
              onClick={() => setIsLogin(true)}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Sign in here
            </button>
          </p>
        )}
      </div>

      {/* Terms and Privacy */}
      <div className="mt-4 text-center text-xs text-gray-500">
        By {isLogin ? 'signing in' : 'creating an account'}, you agree to our{' '}
        <a href="#" className="hover:text-gray-700 underline">Terms of Service</a>{' '}
        and{' '}
        <a href="#" className="hover:text-gray-700 underline">Privacy Policy</a>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { User, LogOut, Database, AlertCircle } from 'lucide-react';

interface AuthStatusProps {
  onLogout?: () => void;
}

export default function AuthStatus({ onLogout }: AuthStatusProps) {
  const [user, setUser] = useState<any>(null);
  const [isChecking, setIsChecking] = useState(true);
  const [authMethod, setAuthMethod] = useState<'supabase' | 'mock' | 'none'>('none');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      // Check if user data exists in localStorage
      const userData = localStorage.getItem('user');
      if (userData) {
        setUser(JSON.parse(userData));
        
        // Try to validate with the API to determine auth method
        try {
          const response = await fetch('/api/auth/session');
          if (response.ok) {
            setAuthMethod('supabase');
          } else {
            setAuthMethod('mock');
          }
        } catch {
          setAuthMethod('mock');
        }
      } else {
        setAuthMethod('none');
      }
    } catch (error) {
      console.error('Auth status check failed:', error);
      setAuthMethod('none');
    } finally {
      setIsChecking(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      localStorage.removeItem('user');
      setUser(null);
      setAuthMethod('none');
      if (onLogout) onLogout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  if (isChecking) {
    return (
      <div className="flex items-center space-x-2 p-3 bg-gray-100 rounded-lg">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
        <span className="text-sm text-gray-600">Checking authentication status...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center space-x-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <AlertCircle className="w-4 h-4 text-yellow-600" />
        <span className="text-sm text-yellow-800">No active session</span>
      </div>
    );
  }

  const getAuthMethodIcon = () => {
    switch (authMethod) {
      case 'supabase':
        return <Database className="w-4 h-4 text-green-600" />;
      case 'mock':
        return <User className="w-4 h-4 text-blue-600" />;
      default:
        return <User className="w-4 h-4 text-gray-600" />;
    }
  };

  const getAuthMethodText = () => {
    switch (authMethod) {
      case 'supabase':
        return 'Supabase Auth';
      case 'mock':
        return 'Mock Auth (Dev)';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
            {user.name ? user.name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{user.name || 'User'}</h3>
            <p className="text-sm text-gray-600">{user.email}</p>
            <div className="flex items-center space-x-2 mt-1">
              {getAuthMethodIcon()}
              <span className="text-xs text-gray-500">{getAuthMethodText()}</span>
            </div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          title="Logout"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

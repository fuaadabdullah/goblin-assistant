"use client";

import { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, AlertTriangle, Lock } from 'lucide-react';

interface SecurityEvent {
  id: string;
  type: 'login' | 'api_access' | 'permission' | 'suspicious';
  user: string;
  ip: string;
  timestamp: string;
  status: 'success' | 'failure' | 'blocked';
  details: string;
}

export default function SecurityPage() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalLogins: 0,
    failedAttempts: 0,
    activeSessions: 0,
    blockedIPs: 0
  });

  // Mock data for demonstration
  const mockEvents: SecurityEvent[] = [
    {
      id: '1',
      type: 'login',
      user: 'admin@goblin.com',
      ip: '192.168.1.100',
      timestamp: '2025-01-15 11:30:00',
      status: 'success',
      details: 'Successful login'
    },
    {
      id: '2',
      type: 'api_access',
      user: 'user@example.com',
      ip: '203.0.113.45',
      timestamp: '2025-01-15 11:25:00',
      status: 'blocked',
      details: 'Rate limit exceeded'
    },
    {
      id: '3',
      type: 'suspicious',
      user: 'unknown',
      ip: '198.51.100.23',
      timestamp: '2025-01-15 11:20:00',
      status: 'blocked',
      details: 'Multiple failed login attempts'
    }
  ];

  const mockStats = {
    totalLogins: 1247,
    failedAttempts: 23,
    activeSessions: 45,
    blockedIPs: 8
  };

  const fetchSecurityData = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setEvents(mockEvents);
      setStats(mockStats);
    } catch (error) {
      console.error('Failed to fetch security data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSecurityData();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failure':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'blocked':
        return <Lock className="h-4 w-4 text-red-500" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'failure':
        return 'bg-yellow-50 border-yellow-200';
      case 'blocked':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const blockIP = async (ip: string) => {
    // Simulate blocking IP
    console.log('Blocking IP:', ip);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Security Dashboard</h1>
            <p className="text-sm text-gray-600 mt-1">
              Monitor security events and access patterns
            </p>
          </div>
          <button
            onClick={fetchSecurityData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Total Logins</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totalLogins}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-yellow-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Failed Attempts</p>
              <p className="text-2xl font-bold text-gray-900">{stats.failedAttempts}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Lock className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Active Sessions</p>
              <p className="text-2xl font-bold text-gray-900">{stats.activeSessions}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Lock className="h-8 w-8 text-red-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Blocked IPs</p>
              <p className="text-2xl font-bold text-gray-900">{stats.blockedIPs}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Security Events */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Security Events</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {events.map((event) => (
              <div key={event.id} className={`border rounded-lg p-4 ${getStatusColor(event.status)}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(event.status)}
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">
                        {event.type.charAt(0).toUpperCase() + event.type.slice(1)} - {event.user}
                      </h3>
                      <p className="text-xs text-gray-600">
                        IP: {event.ip} • {event.timestamp}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {event.status === 'blocked' && (
                      <button
                        onClick={() => blockIP(event.ip)}
                        className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                      >
                        Block IP
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-700">{event.details}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

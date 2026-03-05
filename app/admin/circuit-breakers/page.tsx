"use client";

import { useState, useEffect } from 'react';
import { RefreshCw, XCircle, AlertTriangle, CheckCircle } from 'lucide-react';

interface CircuitBreaker {
  id: string;
  name: string;
  service: string;
  status: 'closed' | 'open' | 'half-open';
  failureRate: number;
  lastFailure?: string;
  requests: number;
  failures: number;
  recoveryTimeout: number;
}

export default function CircuitBreakersPage() {
  const [circuitBreakers, setCircuitBreakers] = useState<CircuitBreaker[]>([]);
  const [loading, setLoading] = useState(false);

  // Mock data for demonstration
  const mockCircuitBreakers: CircuitBreaker[] = [
    {
      id: '1',
      name: 'OpenAI API',
      service: 'openai',
      status: 'closed',
      failureRate: 2.1,
      requests: 1247,
      failures: 26,
      recoveryTimeout: 60
    },
    {
      id: '2', 
      name: 'Anthropic API',
      service: 'anthropic',
      status: 'open',
      failureRate: 45.2,
      lastFailure: '2025-01-15 10:30:00',
      requests: 89,
      failures: 40,
      recoveryTimeout: 120
    },
    {
      id: '3',
      name: 'Redis Cache',
      service: 'redis',
      status: 'half-open',
      failureRate: 8.7,
      requests: 345,
      failures: 30,
      recoveryTimeout: 30
    }
  ];

  const fetchCircuitBreakers = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setCircuitBreakers(mockCircuitBreakers);
    } catch (error) {
      console.error('Failed to fetch circuit breakers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCircuitBreakers();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'closed':
        return 'text-green-600 bg-green-100';
      case 'open':
        return 'text-red-600 bg-red-100';
      case 'half-open':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'closed':
        return <CheckCircle className="h-4 w-4" />;
      case 'open':
        return <XCircle className="h-4 w-4" />;
      case 'half-open':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  const resetCircuitBreaker = async (id: string) => {
    // Simulate reset action
    setCircuitBreakers(prev => 
      prev.map(cb => 
        cb.id === id 
          ? { ...cb, status: 'closed' as const, failureRate: 0, failures: 0 }
          : cb
      )
    );
  };

  const openCircuitBreaker = async (id: string) => {
    // Simulate open action
    setCircuitBreakers(prev => 
      prev.map(cb => 
        cb.id === id 
          ? { ...cb, status: 'open' as const }
          : cb
      )
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Circuit Breakers</h1>
            <p className="text-sm text-gray-600 mt-1">
              Monitor and manage circuit breaker states for external services
            </p>
          </div>
          <button
            onClick={fetchCircuitBreakers}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Circuit Breakers List */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Service Circuit Breakers</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {circuitBreakers.map((cb) => (
              <div key={cb.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(cb.status)}`}>
                      {getStatusIcon(cb.status)}
                      <span className="capitalize">{cb.status}</span>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{cb.name}</h3>
                      <p className="text-xs text-gray-600">Service: {cb.service}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">{cb.failureRate}% failure rate</p>
                      <p className="text-xs text-gray-600">
                        {cb.failures}/{cb.requests} requests failed
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      {cb.status !== 'closed' && (
                        <button
                          onClick={() => resetCircuitBreaker(cb.id)}
                          className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          Reset
                        </button>
                      )}
                      {cb.status === 'closed' && (
                        <button
                          onClick={() => openCircuitBreaker(cb.id)}
                          className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                        >
                          Force Open
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                
                {cb.lastFailure && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs text-gray-600">
                      Last failure: {cb.lastFailure}
                    </p>
                    <p className="text-xs text-gray-600">
                      Recovery timeout: {cb.recoveryTimeout} seconds
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Status Legend */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Circuit Breaker States</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium text-green-600 bg-green-100">
              <CheckCircle className="h-4 w-4" />
              <span>Closed</span>
            </div>
            <p className="text-sm text-gray-600">Normal operation</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium text-red-600 bg-red-100">
              <XCircle className="h-4 w-4" />
              <span>Open</span>
            </div>
            <p className="text-sm text-gray-600">Blocking requests</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium text-yellow-600 bg-yellow-100">
              <AlertTriangle className="h-4 w-4" />
              <span>Half-Open</span>
            </div>
            <p className="text-sm text-gray-600">Testing recovery</p>
          </div>
        </div>
      </div>
    </div>
  );
}

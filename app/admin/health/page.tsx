"use client";

import { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, AlertTriangle, XCircle, Clock } from 'lucide-react';

interface HealthStatus {
  service: string;
  status: 'healthy' | 'warning' | 'error';
  responseTime?: number;
  lastCheck: string;
  details?: string;
}

export default function AdminHealthPage() {
  const [healthData, setHealthData] = useState<HealthStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const fetchHealthData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/ops/health/summary');
      const data = await response.json();
      
      // Transform API data to our interface
      const healthStatus: HealthStatus[] = [
        {
          service: 'API Server',
          status: data.api_server === 'healthy' ? 'healthy' : data.api_server === 'degraded' ? 'warning' : 'error',
          responseTime: data.api_response_time,
          lastCheck: new Date().toLocaleString(),
          details: data.api_server_message
        },
        {
          service: 'Database',
          status: data.database === 'healthy' ? 'healthy' : data.database === 'degraded' ? 'warning' : 'error',
          responseTime: data.db_response_time,
          lastCheck: new Date().toLocaleString(),
          details: data.database_message
        },
        {
          service: 'Redis Cache',
          status: data.redis === 'healthy' ? 'healthy' : data.redis === 'degraded' ? 'warning' : 'error',
          responseTime: data.redis_response_time,
          lastCheck: new Date().toLocaleString(),
          details: data.redis_message
        },
        {
          service: 'Queue System',
          status: data.queue === 'healthy' ? 'healthy' : data.queue === 'degraded' ? 'warning' : 'error',
          lastCheck: new Date().toLocaleString(),
          details: data.queue_message
        }
      ];
      
      setHealthData(healthStatus);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch health data:', error);
      setHealthData([
        {
          service: 'API Server',
          status: 'error',
          lastCheck: new Date().toLocaleString(),
          details: 'Failed to connect to health endpoint'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-50 border-green-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const healthyCount = healthData.filter(h => h.status === 'healthy').length;
  const warningCount = healthData.filter(h => h.status === 'warning').length;
  const errorCount = healthData.filter(h => h.status === 'error').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
            <p className="text-sm text-gray-600 mt-1">
              Monitor the health status of all system components
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-500">
              {lastUpdate && (
                <>Last updated: {lastUpdate.toLocaleTimeString()}</>
              )}
            </div>
            <button
              onClick={fetchHealthData}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <CheckCircle className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Healthy</p>
              <p className="text-2xl font-bold text-gray-900">{healthyCount}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-yellow-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Warning</p>
              <p className="text-2xl font-bold text-gray-900">{warningCount}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <XCircle className="h-8 w-8 text-red-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Error</p>
              <p className="text-2xl font-bold text-gray-900">{errorCount}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Clock className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Total Services</p>
              <p className="text-2xl font-bold text-gray-900">{healthData.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Health Details */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Service Health Details</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {healthData.map((service, index) => (
              <div
                key={index}
                className={`border rounded-lg p-4 ${getStatusColor(service.status)}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">
                        {service.service}
                      </h3>
                      <p className="text-xs text-gray-600">
                        Last checked: {service.lastCheck}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-medium text-gray-900 capitalize">
                      {service.status}
                    </span>
                    {service.responseTime && (
                      <p className="text-xs text-gray-600">
                        {service.responseTime}ms
                      </p>
                    )}
                  </div>
                </div>
                {service.details && (
                  <div className="mt-3 p-3 bg-white bg-opacity-50 rounded border">
                    <p className="text-sm text-gray-700">{service.details}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

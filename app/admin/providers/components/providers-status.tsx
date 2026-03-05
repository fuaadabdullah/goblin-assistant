"use client";

import { useState, useEffect } from "react";
import { Card, Badge, Button } from "@/components/ui";
import { 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle, 
  Settings,
  Activity,
  TrendingUp
} from "lucide-react";
import { TooltipProvider } from "@/components/ui/Tooltip";

interface ProviderData {
  name: string;
  status: string;
  last_check: number | null;
  latency_ms: number;
  error: string | null;
  capabilities: string[];
  models: string[];
  priority_tier: number;
  circuit_breaker: {
    state: string;
    failure_count: number;
    failure_threshold: number;
    last_failure_time: number;
    time_until_recovery: number;
  };
  performance: {
    avg_response_time: number;
    min_response_time: number;
    max_response_time: number;
    p95_response_time: number;
    error_rate: number;
    total_requests: number;
    error_count: number;
  };
  health_score: number;
}

interface ProvidersResponse {
  timestamp: string;
  providers: Record<string, ProviderData>;
  summary: {
    total_providers: number;
    healthy_providers: number;
    unhealthy_providers: number;
    open_circuit_breakers: number;
    avg_latency: number;
  };
}

export function ProvidersStatus() {
  const [providersData, setProvidersData] = useState<ProvidersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Wrap in TooltipProvider to fix the build error
  return (
    <TooltipProvider>
      <ProvidersStatusContent 
        providersData={providersData}
        loading={loading}
        error={error}
        setProvidersData={setProvidersData}
        setLoading={setLoading}
        setError={setError}
      />
    </TooltipProvider>
  );
}

function ProvidersStatusContent({ 
  providersData, 
  loading, 
  error, 
  setProvidersData, 
  setLoading, 
  setError 
}: {
  providersData: ProvidersResponse | null;
  loading: boolean;
  error: string | null;
  setProvidersData: React.Dispatch<React.SetStateAction<ProvidersResponse | null>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
}) {

  const fetchProvidersData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/ops/providers/status');
      if (!response.ok) {
        throw new Error('Failed to fetch provider data');
      }
      const data = await response.json();
      setProvidersData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProvidersData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchProvidersData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'default';
      case 'degraded': return 'secondary';
      case 'unhealthy': return 'destructive';
      default: return 'outline';
    }
  };

  const getCircuitBreakerColor = (state: string) => {
    switch (state) {
      case 'CLOSED': return 'default';
      case 'OPEN': return 'destructive';
      case 'HALF_OPEN': return 'secondary';
      default: return 'outline';
    }
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'danger';
  };

  const formatLatency = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  const formatLastCheck = (timestamp: number | null) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin text-indigo-600" />
          <span>Loading provider status...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200">
        <div className="p-6">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Provider Data</h3>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
            <Button variant="primary" size="sm" onClick={fetchProvidersData}>
              Retry
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (!providersData) {
    return null;
  }

  const { providers, summary } = providersData;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-green-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Healthy Providers</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.healthy_providers}/{summary.total_providers}
                </h3>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
          </div>
        </Card>

        <Card className="border-yellow-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Unhealthy Providers</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.unhealthy_providers}
                </h3>
              </div>
              <AlertTriangle className="h-8 w-8 text-yellow-500" />
            </div>
          </div>
        </Card>

        <Card className="border-red-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Open Circuit Breakers</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {summary.open_circuit_breakers}
                </h3>
              </div>
              <Activity className="h-8 w-8 text-red-500" />
            </div>
          </div>
        </Card>

        <Card className="border-blue-200">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Avg Latency</p>
                <h3 className="text-2xl font-bold text-gray-900 mt-1">
                  {formatLatency(summary.avg_latency)}
                </h3>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
          </div>
        </Card>
      </div>

      {/* Providers Table */}
      <Card className="border-gray-200">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Provider Matrix</h3>
            <Button variant="ghost" size="sm" onClick={fetchProvidersData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Provider</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Health Score</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Latency</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Circuit Breaker</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Error Rate</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Last Check</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(providers).map(([name, provider]) => (
                  <tr key={name} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4 px-4">
                      <div>
                        <div className="font-medium text-gray-900">{name}</div>
                        <div className="text-sm text-gray-500">
                          Tier {provider.priority_tier} • {provider.capabilities.join(', ')}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <Badge variant={getStatusColor(provider.status)}>
                        {provider.status}
                      </Badge>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              getHealthScoreColor(provider.health_score) === 'success' ? 'bg-green-500' :
                              getHealthScoreColor(provider.health_score) === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${provider.health_score}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{provider.health_score}/100</span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="text-sm font-medium">
                        {formatLatency(provider.latency_ms)}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <Badge variant={getCircuitBreakerColor(provider.circuit_breaker.state)}>
                        {provider.circuit_breaker.state}
                      </Badge>
                      {provider.circuit_breaker.state === 'OPEN' && (
                        <div className="text-xs text-gray-500 mt-1">
                          {Math.ceil(provider.circuit_breaker.time_until_recovery)}s until recovery
                        </div>
                      )}
                    </td>
                    <td className="py-4 px-4">
                      <span className={`text-sm font-medium ${
                        provider.performance.error_rate > 5 ? 'text-red-600' : 
                        provider.performance.error_rate > 1 ? 'text-yellow-600' : 'text-green-600'
                      }`}>
                        {provider.performance.error_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className="text-sm text-gray-600">
                        {formatLastCheck(provider.last_check)}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex space-x-2">
                        <Button variant="ghost" size="sm" className="text-xs">
                          <Settings className="h-3 w-3 mr-1" />
                          Reset CB
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
}

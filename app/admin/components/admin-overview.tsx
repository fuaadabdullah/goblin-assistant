"use client";

import { useState, useEffect } from "react";
import { Card, Badge, Button } from "@/components/ui";
import { AlertTriangle, RefreshCw, Server, BarChart3, Database, Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react";

interface HealthData {
  status: string;
  timestamp: string;
  uptime: {
    seconds: number;
    formatted: string;
  };
  components: {
    api: { status: string };
    routing: { status: string };
    database: { status: string };
    redis: { status: string };
    providers: { status: string };
    security: { status: string };
  };
  summary: {
    total_components: number;
    healthy_components: number;
    degraded_components: number;
    warning_components: number;
  };
}

export function AdminOverview() {
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealthData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/ops/health/summary');
      if (!response.ok) {
        throw new Error('Failed to fetch health data');
      }
      const data = await response.json();
      setHealthData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  const getStatusIcon = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower === 'healthy' || statusLower === 'ok') {
      return <CheckCircle className="h-8 w-8 text-green-500" />;
    } else if (statusLower === 'degraded' || statusLower === 'warning') {
      return <AlertCircle className="h-8 w-8 text-yellow-500" />;
    } else {
      return <XCircle className="h-8 w-8 text-red-500" />;
    }
  };

  const getComponentStatus = (component: { status: string }) => {
    return component.status.toLowerCase();
  };

  const getStatusColor = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower === 'healthy' || statusLower === 'ok') {
      return 'success';
    } else if (statusLower === 'degraded' || statusLower === 'warning') {
      return 'warning';
    } else {
      return 'error';
    }
  };

  if (error) {
    return (
      <Card className="border-red-200">
        <div className="p-6">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="h-6 w-6 text-red-500" />
            <div>
              <h3 className="font-semibold text-red-900">Error Loading Health Data</h3>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
            <Button variant="default" size="sm" onClick={fetchHealthData}>
              Retry
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (!healthData) {
    return null;
  }

  const overallStatus = healthData.status;
  const healthyComponents = healthData.summary.healthy_components;
  const totalComponents = healthData.summary.total_components;
  const uptime = healthData.uptime.formatted;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* System Status Card */}
      <Card className="border-indigo-200">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">System Status</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">
                {overallStatus.toUpperCase()}
              </h3>
            </div>
            {getStatusIcon(overallStatus)}
          </div>
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Components:</span>
              <span className="font-medium">{healthyComponents}/{totalComponents} healthy</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Uptime:</span>
              <span className="font-medium">{uptime}</span>
            </div>
          </div>
          <div className="mt-4">
            <Button variant="ghost" size="sm" onClick={fetchHealthData} className="w-full">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Status
            </Button>
          </div>
        </div>
      </Card>

      {/* Components Status */}
      <Card className="border-gray-200">
        <div className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Component Status</h3>
          <div className="space-y-3">
            {Object.entries(healthData.components).map(([name, component]) => {
              const status = getComponentStatus(component);
              return (
                <div key={name} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      status === 'healthy' ? 'bg-green-500' : 
                      status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                    }`} />
                    <span className="text-sm font-medium capitalize">
                      {name.replace('_', ' ')}
                    </span>
                  </div>
                  <Badge variant={getStatusColor(status) === 'success' ? 'default' : getStatusColor(status) === 'warning' ? 'secondary' : 'destructive'}>
                    {status}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className="border-blue-200">
        <div className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Button variant="ghost" size="sm" className="justify-start w-full">
              <Server className="h-4 w-4 mr-2" />
              Provider Status
            </Button>
            <Button variant="ghost" size="sm" className="justify-start w-full">
              <BarChart3 className="h-4 w-4 mr-2" />
              Performance Metrics
            </Button>
            <Button variant="ghost" size="sm" className="justify-start w-full">
              <Database className="h-4 w-4 mr-2" />
              Cache Status
            </Button>
            <Button variant="ghost" size="sm" className="justify-start w-full">
              <Clock className="h-4 w-4 mr-2" />
              Task Queues
            </Button>
          </div>
        </div>
      </Card>

      {/* System Info */}
      <Card className="border-purple-200">
        <div className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">System Info</h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Last Updated:</span>
              <span className="font-medium">{new Date(healthData.timestamp).toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">API Status:</span>
              <Badge variant={getStatusColor(getComponentStatus(healthData.components.api)) === 'success' ? 'default' : getStatusColor(getComponentStatus(healthData.components.api)) === 'warning' ? 'secondary' : 'destructive'}>
                {getComponentStatus(healthData.components.api)}
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Redis Status:</span>
              <Badge variant={getStatusColor(getComponentStatus(healthData.components.redis)) === 'success' ? 'default' : getStatusColor(getComponentStatus(healthData.components.redis)) === 'warning' ? 'secondary' : 'destructive'}>
                {getComponentStatus(healthData.components.redis)}
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Routing Status:</span>
              <Badge variant={getStatusColor(getComponentStatus(healthData.components.routing)) === 'success' ? 'default' : getStatusColor(getComponentStatus(healthData.components.routing)) === 'warning' ? 'secondary' : 'destructive'}>
                {getComponentStatus(healthData.components.routing)}
              </Badge>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

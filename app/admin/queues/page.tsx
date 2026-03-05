"use client";

import { useState, useEffect } from 'react';
import { RefreshCw, Clock, Play, Pause, AlertTriangle } from 'lucide-react';

interface TaskQueue {
  id: string;
  name: string;
  type: string;
  status: 'running' | 'paused' | 'stopped';
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  lastActivity: string;
}

export default function QueuesPage() {
  const [queues, setQueues] = useState<TaskQueue[]>([]);
  const [loading, setLoading] = useState(false);

  // Mock data for demonstration
  const mockQueues: TaskQueue[] = [
    {
      id: '1',
      name: 'AI Processing Queue',
      type: 'ai_tasks',
      status: 'running',
      pending: 23,
      processing: 5,
      completed: 1247,
      failed: 12,
      lastActivity: '2025-01-15 11:30:00'
    },
    {
      id: '2',
      name: 'Email Notifications',
      type: 'notifications',
      status: 'running',
      pending: 8,
      processing: 2,
      completed: 892,
      failed: 3,
      lastActivity: '2025-01-15 11:29:45'
    },
    {
      id: '3',
      name: 'Data Cleanup',
      type: 'maintenance',
      status: 'paused',
      pending: 156,
      processing: 0,
      completed: 3400,
      failed: 23,
      lastActivity: '2025-01-15 10:15:00'
    }
  ];

  const fetchQueues = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setQueues(mockQueues);
    } catch (error) {
      console.error('Failed to fetch queues:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueues();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 bg-green-100';
      case 'paused':
        return 'text-yellow-600 bg-yellow-100';
      case 'stopped':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Play className="h-4 w-4" />;
      case 'paused':
        return <Pause className="h-4 w-4" />;
      case 'stopped':
        return <AlertTriangle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const toggleQueue = async (id: string) => {
    setQueues(prev => 
      prev.map(queue => 
        queue.id === id 
          ? { 
              ...queue, 
              status: queue.status === 'running' ? 'paused' : 'running' as const 
            }
          : queue
      )
    );
  };

  const totalTasks = queues.reduce((sum, q) => sum + q.pending + q.processing + q.completed + q.failed, 0);
  const runningQueues = queues.filter(q => q.status === 'running').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Task Queues</h1>
            <p className="text-sm text-gray-600 mt-1">
              Monitor and manage background task processing queues
            </p>
          </div>
          <button
            onClick={fetchQueues}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Play className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Running Queues</p>
              <p className="text-2xl font-bold text-gray-900">{runningQueues}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Clock className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Pending Tasks</p>
              <p className="text-2xl font-bold text-gray-900">
                {queues.reduce((sum, q) => sum + q.pending, 0)}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <RefreshCw className="h-8 w-8 text-orange-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Processing</p>
              <p className="text-2xl font-bold text-gray-900">
                {queues.reduce((sum, q) => sum + q.processing, 0)}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <AlertTriangle className="h-8 w-8 text-red-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Failed Tasks</p>
              <p className="text-2xl font-bold text-gray-900">
                {queues.reduce((sum, q) => sum + q.failed, 0)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Queues List */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Queue Details</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {queues.map((queue) => (
              <div key={queue.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(queue.status)}`}>
                      {getStatusIcon(queue.status)}
                      <span className="capitalize">{queue.status}</span>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{queue.name}</h3>
                      <p className="text-xs text-gray-600">Type: {queue.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        {queue.pending + queue.processing + queue.completed + queue.failed} total tasks
                      </p>
                      <p className="text-xs text-gray-600">
                        Last activity: {queue.lastActivity}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => toggleQueue(queue.id)}
                        className={`px-3 py-1 text-xs rounded ${
                          queue.status === 'running'
                            ? 'bg-yellow-600 text-white hover:bg-yellow-700'
                            : 'bg-green-600 text-white hover:bg-green-700'
                        }`}
                      >
                        {queue.status === 'running' ? 'Pause' : 'Resume'}
                      </button>
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-xs text-gray-600">Pending</p>
                      <p className="text-lg font-bold text-blue-600">{queue.pending}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Processing</p>
                      <p className="text-lg font-bold text-orange-600">{queue.processing}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Completed</p>
                      <p className="text-lg font-bold text-green-600">{queue.completed}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">Failed</p>
                      <p className="text-lg font-bold text-red-600">{queue.failed}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

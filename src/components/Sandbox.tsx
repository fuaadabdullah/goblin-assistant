"use client";

import React, { useState, useEffect } from 'react';
import { Play, Square, Download, FileText, Clock, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/Select';
import { Textarea } from './ui/Textarea';
import { Alert, AlertDescription } from './ui/Alert';
import { useTranslation } from '@/i18n';
import toast from 'react-hot-toast';

interface SandboxJob {
  job_id: string;
  status: 'queued' | 'running' | 'finished' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  finished_at?: string;
  exit_code?: number;
  error?: string;
}

interface SandboxArtifact {
  name: string;
  size: number;
  url: string;
  created_at: string;
}

const SUPPORTED_LANGUAGES = [
  { value: 'python', label: 'Python', extension: 'py' },
  { value: 'javascript', label: 'JavaScript', extension: 'js' },
  { value: 'bash', label: 'Bash', extension: 'sh' }
];

export function Sandbox() {
  const { t } = useTranslation();
  const [isEnabled, setIsEnabled] = useState(false);
  const [language, setLanguage] = useState('python');
  const [source, setSource] = useState('');
  const [timeout, setTimeout] = useState(10);
  const [runtimeArgs, setRuntimeArgs] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Job tracking
  const [currentJob, setCurrentJob] = useState<SandboxJob | null>(null);
  const [jobLogs, setJobLogs] = useState('');
  const [artifacts, setArtifacts] = useState<SandboxArtifact[]>([]);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Check if sandbox is enabled
  useEffect(() => {
    checkSandboxStatus();
  }, []);

  // Poll job status
  useEffect(() => {
    if (currentJob && ['queued', 'running'].includes(currentJob.status)) {
      const interval = setInterval(pollJobStatus, 2000);
      setPollingInterval(interval);
      return () => clearInterval(interval);
    } else if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [currentJob]);

  const checkSandboxStatus = async () => {
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api/sandbox/health/status`);
      const data = await response.json();
      setIsEnabled(data.status === 'healthy');
    } catch (error) {
      console.error('Failed to check sandbox status:', error);
      setIsEnabled(false);
    }
  };

  const submitJob = async () => {
    if (!source.trim()) {
      toast.error('Please enter some code to execute');
      return;
    }

    setIsSubmitting(true);
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api/sandbox/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        },
        body: JSON.stringify({
          language,
          source: source.trim(),
          timeout,
          runtime_args: runtimeArgs.trim()
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to submit job');
      }

      const data = await response.json();
      const job: SandboxJob = {
        job_id: data.job_id,
        status: 'queued',
        created_at: new Date().toISOString()
      };

      setCurrentJob(job);
      toast.success('Job submitted successfully');
    } catch (error) {
      console.error('Failed to submit job:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to submit job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const pollJobStatus = async () => {
    if (!currentJob) return;

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api/sandbox/status/${currentJob.job_id}`, {
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to get job status');
      }

      const job = await response.json();
      setCurrentJob(job);

      // If job is complete, fetch logs and artifacts
      if (['finished', 'failed'].includes(job.status)) {
        await fetchJobLogs();
        await fetchJobArtifacts();
      }
    } catch (error) {
      console.error('Failed to poll job status:', error);
    }
  };

  const fetchJobLogs = async () => {
    if (!currentJob) return;

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api/sandbox/logs/${currentJob.job_id}`, {
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setJobLogs(data.logs || '');
      }
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  const fetchJobArtifacts = async () => {
    if (!currentJob) return;

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api/sandbox/artifacts/${currentJob.job_id}`, {
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setArtifacts(data.artifacts || []);
      }
    } catch (error) {
      console.error('Failed to fetch artifacts:', error);
    }
  };

  const cancelJob = async () => {
    if (!currentJob) return;

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      await fetch(`${apiBaseUrl}/api/sandbox/cancel/${currentJob.job_id}`, {
        method: 'POST',
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        }
      });
      toast.success('Job cancelled');
    } catch (error) {
      console.error('Failed to cancel job:', error);
      toast.error('Failed to cancel job');
    }
  };

  const downloadArtifact = async (artifact: SandboxArtifact) => {
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';
      const response = await fetch(`${apiBaseUrl}/api${artifact.url}`, {
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || 'devkey'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to download artifact');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = artifact.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download artifact:', error);
      toast.error('Failed to download artifact');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'running': return <Loader className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'finished': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed': return <XCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled': return <AlertCircle className="w-4 h-4 text-gray-500" />;
      default: return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued': return 'bg-yellow-100 text-yellow-800';
      case 'running': return 'bg-blue-100 text-blue-800';
      case 'finished': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'cancelled': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isEnabled) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Sandbox execution is currently disabled or not available.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Code Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="w-5 h-5" />
            Code Execution Sandbox
          </CardTitle>
          <CardDescription>
            Execute code securely in isolated containers
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Language and Timeout */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-2">Language</label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-32">
              <label className="block text-sm font-medium mb-2">Timeout (s)</label>
              <input
                type="number"
                min="1"
                max="300"
                value={timeout}
                onChange={(e) => setTimeout(parseInt(e.target.value) || 10)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Runtime Arguments */}
          <div>
            <label className="block text-sm font-medium mb-2">Runtime Arguments (optional)</label>
            <input
              type="text"
              value={runtimeArgs}
              onChange={(e) => setRuntimeArgs(e.target.value)}
              placeholder="Additional command line arguments"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Code Editor */}
          <div>
            <label className="block text-sm font-medium mb-2">Code</label>
            <Textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder={`Enter your ${SUPPORTED_LANGUAGES.find(l => l.value === language)?.label} code here...`}
              rows={10}
              className="font-mono"
            />
          </div>

          {/* Submit Button */}
          <Button
            onClick={submitJob}
            disabled={isSubmitting || !source.trim()}
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Loader className="w-4 h-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Execute Code
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Job Status */}
      {currentJob && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getStatusIcon(currentJob.status)}
                Job {currentJob.job_id.slice(0, 8)}
              </div>
              <Badge className={getStatusColor(currentJob.status)}>
                {currentJob.status.toUpperCase()}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Job Details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Created:</span>{' '}
                {new Date(currentJob.created_at).toLocaleString()}
              </div>
              {currentJob.started_at && (
                <div>
                  <span className="font-medium">Started:</span>{' '}
                  {new Date(currentJob.started_at).toLocaleString()}
                </div>
              )}
              {currentJob.finished_at && (
                <div>
                  <span className="font-medium">Finished:</span>{' '}
                  {new Date(currentJob.finished_at).toLocaleString()}
                </div>
              )}
              {currentJob.exit_code !== undefined && (
                <div>
                  <span className="font-medium">Exit Code:</span>{' '}
                  {currentJob.exit_code}
                </div>
              )}
            </div>

            {/* Error Message */}
            {currentJob.error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{currentJob.error}</AlertDescription>
              </Alert>
            )}

            {/* Cancel Button */}
            {['queued', 'running'].includes(currentJob.status) && (
              <Button
                onClick={cancelJob}
                variant="outline"
                className="w-full"
              >
                <Square className="w-4 h-4 mr-2" />
                Cancel Job
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Logs */}
      {jobLogs && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Execution Output
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-900 text-green-400 p-4 rounded-md overflow-x-auto text-sm font-mono whitespace-pre-wrap">
              {jobLogs}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Artifacts */}
      {artifacts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="w-5 h-5" />
              Generated Files ({artifacts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {artifacts.map((artifact) => (
                <div key={artifact.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                  <div>
                    <div className="font-medium">{artifact.name}</div>
                    <div className="text-sm text-gray-500">
                      {(artifact.size / 1024).toFixed(1)} KB • {new Date(artifact.created_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    onClick={() => downloadArtifact(artifact)}
                    variant="outline"
                    size="sm"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
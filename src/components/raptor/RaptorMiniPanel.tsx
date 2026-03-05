import { useEffect, useState } from 'react';
import { raptorStart, raptorStop, raptorStatus, raptorLogs, raptorDemo } from '@/api/api-client';
// import '@/components/cost/CostEstimationPanel.css'; // Temporarily commented for testing
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';

export default function RaptorMiniPanel(): React.JSX.Element {
  const [status, setStatus] = useState<{ running: boolean; config_file?: string } | null>(null);
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

  const refreshStatus = async () => {
    try {
      const s = await raptorStatus();
      setStatus(s);
      setError(null);
    } catch (err: unknown) {
      console.error(err);
      setError('Failed to fetch status');
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  const start = async () => {
    setLoading(true);
    try {
      await raptorStart();
      await refreshStatus();
    } catch (err) {
      setError('Failed to start raptor');
    } finally {
      setLoading(false);
    }
  };

  const stop = async () => {
    setLoading(true);
    try {
      await raptorStop();
      await refreshStatus();
    } catch (err) {
      setError('Failed to stop raptor');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await raptorLogs();
      setLogs(res.log_tail);
    } catch (err) {
      setError('Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  const demoBoom = async () => {
    setLoading(true);
    setError(null);
    try {
      await raptorDemo('boom');
      await fetchLogs();
    } catch (err) {
      setError('Demo failed');
    } finally {
      setLoading(false);
    }
  };

  const copyLogs = async () => {
    if (!logs) return;
    try {
      await navigator.clipboard.writeText(logs);
      setCopyStatus('Copied');
      setTimeout(() => setCopyStatus(null), 1500);
    } catch (err) {
      setCopyStatus('Copy failed');
      setTimeout(() => setCopyStatus(null), 1500);
    }
  };

  return (
    <Card className="raptor-panel">
      <CardHeader>
        <CardTitle>Raptor Mini Demo</CardTitle>
      </CardHeader>
      <CardContent>
        {status && (
          <div className="raptor-status">
            <div>Running: {status.running ? 'Yes' : 'No'}</div>
            <div>Config: {status.config_file ?? 'default'}</div>
          </div>
        )}

        <div className="raptor-controls">
          <Button onClick={start} disabled={loading || !!status?.running}>
            Start
          </Button>
          <Button onClick={stop} disabled={loading || !status?.running}>
            Stop
          </Button>
          <Button onClick={fetchLogs} disabled={loading}>
            Fetch Logs
          </Button>
          <Button onClick={demoBoom} disabled={loading}>
            Trigger Boom
          </Button>
        </div>

        {error && <div className="error">{error}</div>}

        {logs && (
          <div className="raptor-logs">
            <h6>Log Tail</h6>
            <pre className="summary-pre">{logs}</pre>
            <div className="summary-actions">
              <Button aria-label="Copy logs" onClick={copyLogs}>
                Copy logs
              </Button>
              {copyStatus && <Badge>{copyStatus}</Badge>}
            </div>
          </div>
        )}

        <div className="raptor-footer">
          <small>Raptor Mini — Lightweight runtime diagnostics demo</small>
        </div>
      </CardContent>
    </Card>
  );
}

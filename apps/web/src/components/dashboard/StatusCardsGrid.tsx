import StatusCard from '../StatusCard';
import type { ServiceStatus } from '../../hooks/useDashboardData';

interface Props {
  backend: ServiceStatus;
  vectorStore: ServiceStatus;
  mcp: ServiceStatus;
  rag: ServiceStatus;
  sandbox: ServiceStatus;
}

const mapStatus = (
  status: ServiceStatus['status']
): 'healthy' | 'degraded' | 'down' | 'unknown' => {
  if (status === 'healthy') return 'healthy';
  if (status === 'degraded') return 'degraded';
  if (status === 'unhealthy') return 'down';
  return 'unknown';
};

export const StatusCardsGrid = ({ backend, vectorStore, mcp, rag, sandbox }: Props) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <StatusCard
        title="Backend API"
        status={mapStatus(backend.status)}
        meta={[{ label: 'Latency', value: `${backend.latency ?? '--'} ms` }]}
      />
      <StatusCard
        title="Vector Store"
        status={mapStatus(vectorStore.status)}
        meta={[{ label: 'Latency', value: `${vectorStore.latency ?? '--'} ms` }]}
      />
      <StatusCard
        title="MCP"
        status={mapStatus(mcp.status)}
        meta={[{ label: 'Latency', value: `${mcp.latency ?? '--'} ms` }]}
      />
      <StatusCard
        title="RAG"
        status={mapStatus(rag.status)}
        meta={[{ label: 'Latency', value: `${rag.latency ?? '--'} ms` }]}
      />
      <StatusCard
        title="Sandbox"
        status={mapStatus(sandbox.status)}
        meta={[{ label: 'Latency', value: `${sandbox.latency ?? '--'} ms` }]}
      />
    </div>
  );
};

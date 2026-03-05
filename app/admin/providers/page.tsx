import { Metadata } from "next";
import { ProvidersStatus } from "./components/providers-status";

export const metadata: Metadata = {
  title: "Provider Status - Admin Dashboard",
  description: "Monitor provider health and performance metrics",
};

export default function ProvidersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Provider Status Matrix</h1>
        <p className="text-gray-600 mt-2">
          Monitor provider availability, latency, and circuit breaker states
        </p>
      </div>
      
      <ProvidersStatus />
    </div>
  );
}

import { Metadata } from "next";
import { PerformanceSnapshot } from "./components/performance-snapshot";

export const metadata: Metadata = {
  title: "Performance Metrics - Admin Dashboard",
  description: "Monitor system performance and cache metrics",
};

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Performance Metrics</h1>
        <p className="text-gray-600 mt-2">
          Monitor cache hit ratios, response times, and usage patterns
        </p>
      </div>
      
      <PerformanceSnapshot />
    </div>
  );
}

import React from "react";
import { useQuery } from "@tanstack/react-query";
import CostBreakdownChart from "./CostBreakdownChart";
import ProviderUsageChart from "./ProviderUsageChart";
import { runtimeClient } from "../api/tauri-client";

const colors = ["#7c3aed", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#a78bfa"];

const Dashboard: React.FC = () => {
  const { data: costSummary, isLoading: costLoading, error: costError } = useQuery({
    queryKey: ["costSummary"],
    queryFn: () => runtimeClient.getCostSummary(),
  });

  const costData = React.useMemo(() => {
    if (!costSummary?.cost_by_provider) return [];
    return Object.entries(costSummary.cost_by_provider).map(([provider, cost], index) => ({
      name: provider,
      value: cost,
      color: colors[index % colors.length],
    }));
  }, [costSummary]);

  const usageData = React.useMemo(() => {
    if (!costSummary?.cost_by_provider) return [];
    return Object.entries(costSummary.cost_by_provider).map(([provider, cost]) => ({
      name: provider,
      tasks: Math.max(1, Math.round(cost * 10)), // visual approximation
    }));
  }, [costSummary]);

  return (
    <div className="p-8 min-h-[400px] text-slate-100">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
      </div>

      {costLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="animate-pulse bg-slate-800 rounded-lg h-72" />
          <div className="animate-pulse bg-slate-800 rounded-lg h-72" />
        </div>
      ) : costError ? (
        <div className="bg-rose-900 text-rose-100 p-4 rounded-md">Error loading data: {(costError as any)?.message || String(costError)}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 rounded-lg p-4">
            <CostBreakdownChart data={costData} />
          </div>
          <div className="bg-slate-900 rounded-lg p-4">
            <ProviderUsageChart data={usageData} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;

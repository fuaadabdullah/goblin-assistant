import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ChartData {
  name: string;
  value: number;
  color: string;
}

interface CostBreakdownChartProps {
  data: ChartData[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-slate-800 border border-slate-700 rounded-md shadow-lg">
        <p className="label text-sm text-slate-300">{`${label}`}</p>
        <p className="intro text-sm text-white">{`Cost: $${payload[0].value.toFixed(6)}`}</p>
      </div>
    );
  }

  return null;
};

const CostBreakdownChart: React.FC<CostBreakdownChartProps> = ({ data }) => {
  return (
    <>
      <h2 className="text-lg font-semibold mb-4 text-white">Cost Breakdown by Provider</h2>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="name" stroke="#9ca3af" fontSize={12} />
          <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(value) => `$${Number(value).toFixed(4)}`} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(100, 116, 139, 0.1)" }} />
          <Legend iconType="circle" />
          {data.map((entry, index) => (
            <Bar key={`bar-${index}`} dataKey="value" name={entry.name} fill={entry.color} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </>
  );
};

export default CostBreakdownChart;
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
import { useGetPerformanceDashboardQuery } from "./performanceApi";
import { format } from "date-fns";

interface Props {
  partyId: string;
  period?: string;
}

export const KPIDashboard: React.FC<Props> = ({
  partyId,
  period = format(new Date(), "yyyy-MM"),
}) => {
  const { data, isLoading, isError } = useGetPerformanceDashboardQuery({
    party_id: partyId,
    period,
  });

  if (isLoading) return <div>Loading KPI dashboard...</div>;
  if (isError || !data) return <div>Failed to load performance data.</div>;

  const chartData = Object.entries(data.summary).map(([kpi, values]) => ({
    kpi,
    target: values.target,
    actual: values.actual,
    achieved: values.achieved,
  }));

  return (
    <div className="kpi-dashboard">
      <h2>Performance Dashboard — {period}</h2>

      <div className="summary-cards">
        {Object.entries(data.summary).map(([kpi, values]) => (
          <div
            key={kpi}
            className={`kpi-card ${values.achieved ? "kpi-card--achieved" : "kpi-card--missed"}`}
          >
            <h3>{kpi.replace(/_/g, " ")}</h3>
            <p className="kpi-actual">{values.actual.toLocaleString()}</p>
            <p className="kpi-target">Target: {values.target.toLocaleString()}</p>
            <p className="kpi-variance">
              Variance: {values.variance >= 0 ? "+" : ""}{values.variance.toFixed(1)}%
            </p>
          </div>
        ))}
      </div>

      <div className="kpi-chart">
        <h3>Target vs Actual</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="kpi" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="target" fill="#94a3b8" name="Target" />
            <Bar dataKey="actual" fill="#3b82f6" name="Actual" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

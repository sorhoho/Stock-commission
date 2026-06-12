import React from "react";
import {
  useListPayoutRequestsQuery,
  useProcessPayoutRequestMutation,
} from "../commission/commissionApi";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "badge-draft",
  PROCESSING: "badge-warning",
  COMPLETED: "badge-confirmed",
  FAILED: "badge-danger",
};

export const PayoutPage: React.FC = () => {
  const { data: payouts, isLoading } = useListPayoutRequestsQuery({});
  const [processRequest, { isLoading: isProcessing }] = useProcessPayoutRequestMutation();

  if (isLoading) return <div className="page-container">Loading payout requests...</div>;

  const total = payouts?.filter((p) => p.status === "PENDING").reduce((s, p) => s + p.amount, 0) ?? 0;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Payout Requests</h2>
        {total > 0 && (
          <div className="stat-pill">
            Pending: <strong>{total.toFixed(2)} THB</strong>
          </div>
        )}
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Party ID</th>
              <th>Statement ID</th>
              <th>Amount</th>
              <th>Currency</th>
              <th>Scheduled Date</th>
              <th>Processed Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {payouts?.length === 0 && (
              <tr><td colSpan={8} className="empty-state">No payout requests found</td></tr>
            )}
            {payouts?.map((p) => (
              <tr key={p.id}>
                <td className="text-mono text-muted">{p.party_id.slice(0, 8)}…</td>
                <td className="text-mono text-muted">{p.statement_id.slice(0, 8)}…</td>
                <td><strong>{p.amount.toFixed(2)}</strong></td>
                <td>{p.currency}</td>
                <td>{new Date(p.scheduled_date).toLocaleDateString()}</td>
                <td>{p.processed_date ? new Date(p.processed_date).toLocaleDateString() : "—"}</td>
                <td>
                  <span className={STATUS_BADGE[p.status] ?? "badge-default"}>{p.status}</span>
                </td>
                <td>
                  {p.status === "PENDING" && (
                    <button
                      className="btn-sm btn-primary"
                      disabled={isProcessing}
                      onClick={() => processRequest(p.id)}
                    >
                      Process
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

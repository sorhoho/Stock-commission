import React from "react";
import {
  useListCommissionStatementsQuery,
  useConfirmStatementMutation,
} from "./commissionApi";

interface Props {
  partyId: string;
}

const STATUS_BADGE: Record<string, string> = {
  DRAFT: "badge-draft",
  CONFIRMED: "badge-confirmed",
  PAID: "badge-paid",
};

export const CommissionStatement: React.FC<Props> = ({ partyId }) => {
  const { data: statements, isLoading, isError } = useListCommissionStatementsQuery({ party_id: partyId });
  const [confirmStatement, { isLoading: isConfirming }] = useConfirmStatementMutation();

  if (isLoading) return <div className="page-container"><h2>Commission Statements</h2><div>Loading...</div></div>;
  if (isError) return <div className="page-container"><h2>Commission Statements</h2><div className="alert alert--error">API unavailable — check backend</div></div>;

  return (
    <div className="commission-statements">
      <h2>Commission Statements</h2>
      <table>
        <thead>
          <tr>
            <th>Period</th>
            <th>Total Commission</th>
            <th>Currency</th>
            <th>Line Items</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {statements?.map((stmt) => (
            <tr key={stmt.id}>
              <td>{`${stmt.period_year}-${String(stmt.period_month).padStart(2, "0")}`}</td>
              <td>{stmt.total_commission.toFixed(2)}</td>
              <td>{stmt.currency}</td>
              <td>{stmt.line_items_count}</td>
              <td>
                <span className={STATUS_BADGE[stmt.status] ?? "badge-default"}>
                  {stmt.status}
                </span>
              </td>
              <td>
                {stmt.status === "DRAFT" && (
                  <button
                    disabled={isConfirming}
                    onClick={() => confirmStatement(stmt.id)}
                  >
                    Confirm
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

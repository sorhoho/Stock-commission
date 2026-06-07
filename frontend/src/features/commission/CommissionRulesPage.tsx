import React, { useState } from "react";
import { useListAgreementsQuery, useListCommissionRulesQuery } from "./commissionApi";

export const CommissionRulesPage: React.FC = () => {
  const [tab, setTab] = useState<"agreements" | "rules">("agreements");
  const { data: agreements, isLoading: loadingA } = useListAgreementsQuery({});
  const { data: rules, isLoading: loadingR } = useListCommissionRulesQuery({});

  return (
    <div className="page-container">
      <h2>Commission Rules &amp; Agreements</h2>

      <div className="tabs">
        {(["agreements", "rules"] as const).map((t) => (
          <button
            key={t}
            className={`tab-btn ${tab === t ? "tab-btn--active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t === "agreements" ? "Agreements" : "Commission Rules"}
          </button>
        ))}
      </div>

      {tab === "agreements" && (
        <div className="card">
          {loadingA ? (
            <div>Loading agreements...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Party</th>
                  <th>Channel</th>
                  <th>Product Category</th>
                  <th>Valid From</th>
                  <th>Valid To</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {agreements?.items?.length === 0 && (
                  <tr><td colSpan={7} className="empty-state">No agreements found</td></tr>
                )}
                {agreements?.items?.map((a) => (
                  <tr key={a.id}>
                    <td><strong>{a.name}</strong></td>
                    <td className="text-mono text-muted">{a.party_id?.slice(0, 8)}…</td>
                    <td>{a.channel ?? "ALL"}</td>
                    <td>{a.product_category ?? "ALL"}</td>
                    <td>{a.valid_from ? new Date(a.valid_from).toLocaleDateString() : "—"}</td>
                    <td>{a.valid_to ? new Date(a.valid_to).toLocaleDateString() : "—"}</td>
                    <td>
                      <span className={a.status === "ACTIVE" ? "badge-confirmed" : "badge-draft"}>
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === "rules" && (
        <div className="card">
          {loadingR ? (
            <div>Loading rules...</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Agreement</th>
                  <th>Type</th>
                  <th>Tier Min</th>
                  <th>Tier Max</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {rules?.items?.length === 0 && (
                  <tr><td colSpan={5} className="empty-state">No rules found</td></tr>
                )}
                {rules?.items?.map((r) => (
                  <tr key={r.id}>
                    <td className="text-mono text-muted">{r.agreement_id?.slice(0, 8)}…</td>
                    <td><span className="badge-draft">{r.commission_type}</span></td>
                    <td>{r.tier_min_qty ?? "—"}</td>
                    <td>{r.tier_max_qty ?? "—"}</td>
                    <td>
                      {r.commission_type === "PERCENTAGE"
                        ? `${r.commission_value}%`
                        : r.commission_value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
};

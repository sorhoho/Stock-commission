import React, { useState } from "react";
import { useListAuditLogsQuery } from "./auditApi";

const SERVICES = [
  "inventory-service",
  "warehouse-service",
  "sell-out-service",
  "sell-in-service",
  "commission-calculation-service",
  "payout-service",
  "party-service",
];

export const AuditPage: React.FC = () => {
  const [service, setService] = useState("");
  const [entityType, setEntityType] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading } = useListAuditLogsQuery({
    source_service: service || undefined,
    entity_type: entityType || undefined,
    from_date: fromDate || undefined,
    size: 50,
  });

  return (
    <div className="page-container">
      <h2>Audit Log</h2>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="filter-row">
          <div className="form-field">
            <label>Service</label>
            <select value={service} onChange={(e) => setService(e.target.value)}>
              <option value="">All Services</option>
              {SERVICES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label>Entity Type</label>
            <input
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              placeholder="e.g. SaleTransaction"
            />
          </div>
          <div className="form-field">
            <label>From Date</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="card">
        {isLoading ? (
          <div>Loading audit logs...</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Service</th>
                <th>Event Type</th>
                <th>Entity</th>
                <th>Actor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data?.items?.length === 0 && (
                <tr><td colSpan={6} className="empty-state">No audit logs found</td></tr>
              )}
              {data?.items?.map((log) => (
                <React.Fragment key={log.id}>
                  <tr>
                    <td className="text-mono" style={{ fontSize: "12px" }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="text-muted">{log.source_service}</td>
                    <td><strong>{log.event_type}</strong></td>
                    <td>
                      {log.entity_type}{" "}
                      <span className="text-mono text-muted">
                        {log.entity_id?.slice(0, 8)}…
                      </span>
                    </td>
                    <td>{log.actor}</td>
                    <td>
                      <button
                        className="btn-sm"
                        onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                      >
                        {expanded === log.id ? "▲" : "▼"}
                      </button>
                    </td>
                  </tr>
                  {expanded === log.id && (
                    <tr>
                      <td colSpan={6} style={{ background: "#f8fafc", padding: "0.75rem" }}>
                        <pre className="json-payload">
                          {JSON.stringify(log.payload, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

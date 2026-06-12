import React, { useState } from "react";
import {
  useOpenPosSessionMutation,
  useGetPosSessionQuery,
  useClosePosSessionMutation,
  type PosSessionCreate,
} from "./salesApi";

const DEMO_DEALER = "00000000-0000-0000-0000-000000000001";

export const PosSessionPage: React.FC = () => {
  const [form, setForm] = useState<PosSessionCreate>({
    terminal_id: "POS-01",
    dealer_party_id: DEMO_DEALER,
    opened_by: "cashier1",
    opening_cash: 0,
  });
  const [activeSessionId, setActiveSessionId] = useState<string | null>(
    sessionStorage.getItem("active_pos_session")
  );
  const [closingCash, setClosingCash] = useState(0);

  const [openSession, { isLoading: isOpening }] = useOpenPosSessionMutation();
  const [closeSession, { isLoading: isClosing }] = useClosePosSessionMutation();
  const { data: session, refetch } = useGetPosSessionQuery(activeSessionId!, {
    skip: !activeSessionId,
  });

  const handleOpen = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await openSession(form).unwrap();
    sessionStorage.setItem("active_pos_session", result.id);
    setActiveSessionId(result.id);
  };

  const handleClose = async () => {
    if (!activeSessionId) return;
    await closeSession({ id: activeSessionId, body: { closing_cash: closingCash } }).unwrap();
    sessionStorage.removeItem("active_pos_session");
    setActiveSessionId(null);
    await refetch();
  };

  return (
    <div className="page-container">
      <h2>POS Session Management</h2>

      {!activeSessionId ? (
        <div className="card">
          <h3>Open New Session</h3>
          <form onSubmit={handleOpen}>
            <div className="form-grid">
              <div className="form-field">
                <label>Terminal ID</label>
                <input
                  required
                  value={form.terminal_id}
                  onChange={(e) => setForm((f) => ({ ...f, terminal_id: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Opened By</label>
                <input
                  required
                  value={form.opened_by}
                  onChange={(e) => setForm((f) => ({ ...f, opened_by: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Opening Cash</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.opening_cash}
                  onChange={(e) => setForm((f) => ({ ...f, opening_cash: Number(e.target.value) }))}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={isOpening}>
              {isOpening ? "Opening..." : "Open Session"}
            </button>
          </form>
        </div>
      ) : (
        <div className="card">
          <div className="session-status">
            <span className="badge badge-confirmed">OPEN</span>
            <span className="session-id">Session ID: {activeSessionId}</span>
          </div>
          {session && (
            <div className="session-stats">
              <div className="stat">
                <span className="stat-label">Terminal</span>
                <span className="stat-value">{session.terminal_id}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Opened By</span>
                <span className="stat-value">{session.opened_by}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Transactions</span>
                <span className="stat-value">{session.total_transactions}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Total Amount</span>
                <span className="stat-value">{session.total_amount.toFixed(2)} THB</span>
              </div>
              <div className="stat">
                <span className="stat-label">Opening Cash</span>
                <span className="stat-value">{session.opening_cash.toFixed(2)}</span>
              </div>
            </div>
          )}
          <div className="form-row" style={{ marginTop: "1rem" }}>
            <label>Closing Cash</label>
            <input
              type="number"
              min={0}
              step="0.01"
              value={closingCash}
              onChange={(e) => setClosingCash(Number(e.target.value))}
            />
            <button className="btn-danger" onClick={handleClose} disabled={isClosing}>
              {isClosing ? "Closing..." : "Close Session"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

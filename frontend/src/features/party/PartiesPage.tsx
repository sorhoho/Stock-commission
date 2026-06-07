import React, { useState } from "react";
import { useListPartiesQuery, useCreatePartyMutation, type PartyCreate } from "./partyApi";

const TYPE_BADGE: Record<string, string> = {
  DEALER: "badge-confirmed",
  DISTRIBUTOR: "badge-warning",
  EMPLOYEE: "badge-draft",
  CUSTOMER: "badge-default",
};

const STATUS_BADGE: Record<string, string> = {
  ACTIVE: "badge-confirmed",
  INACTIVE: "badge-draft",
  SUSPENDED: "badge-danger",
};

const TYPES = ["DEALER", "DISTRIBUTOR", "EMPLOYEE", "CUSTOMER"] as const;

export const PartiesPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [filterType, setFilterType] = useState<string>("");
  const [form, setForm] = useState<PartyCreate>({
    name: "",
    party_type: "DEALER",
    email: "",
    phone: "",
    address: "",
  });

  const { data, isLoading } = useListPartiesQuery({
    party_type: filterType || undefined,
  });
  const [createParty, { isLoading: isCreating, isSuccess }] = useCreatePartyMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createParty(form).unwrap();
    setShowForm(false);
    setForm({ name: "", party_type: "DEALER", email: "", phone: "", address: "" });
  };

  if (isLoading) return <div className="page-container">Loading parties...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Parties &amp; Dealers</h2>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add Party"}
        </button>
      </div>

      {isSuccess && <div className="alert alert--success">Party created successfully.</div>}

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>Add Party</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label>Name</label>
                <input required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              </div>
              <div className="form-field">
                <label>Type</label>
                <select
                  value={form.party_type}
                  onChange={(e) => setForm((f) => ({ ...f, party_type: e.target.value as PartyCreate["party_type"] }))}
                >
                  {TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label>Email</label>
                <input type="email" value={form.email ?? ""} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="form-field">
                <label>Phone</label>
                <input value={form.phone ?? ""} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
              </div>
              <div className="form-field" style={{ gridColumn: "span 2" }}>
                <label>Address</label>
                <input value={form.address ?? ""} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} />
              </div>
              <div className="form-field">
                <label>Tax ID</label>
                <input value={form.tax_id ?? ""} onChange={(e) => setForm((f) => ({ ...f, tax_id: e.target.value }))} />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={isCreating}>
              {isCreating ? "Saving..." : "Save Party"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem" }}>
          <span style={{ fontWeight: 500 }}>Filter:</span>
          {["", ...TYPES].map((t) => (
            <button
              key={t}
              className={`tab-btn ${filterType === t ? "tab-btn--active" : ""}`}
              onClick={() => setFilterType(t)}
            >
              {t || "All"}
            </button>
          ))}
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.length === 0 && (
              <tr><td colSpan={5} className="empty-state">No parties found</td></tr>
            )}
            {data?.items?.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.name}</strong></td>
                <td><span className={TYPE_BADGE[p.party_type] ?? "badge-default"}>{p.party_type}</span></td>
                <td>{p.email ?? "—"}</td>
                <td>{p.phone ?? "—"}</td>
                <td><span className={STATUS_BADGE[p.status] ?? "badge-default"}>{p.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

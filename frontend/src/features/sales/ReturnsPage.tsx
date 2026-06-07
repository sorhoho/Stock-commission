import React, { useState } from "react";
import {
  useListReturnsQuery,
  useCreateReturnMutation,
  useApproveReturnMutation,
  useRejectReturnMutation,
  type ReturnTransactionCreate,
  type ReturnTransactionItemCreate,
} from "./salesApi";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "badge-draft",
  APPROVED: "badge-confirmed",
  REJECTED: "badge-danger",
};

const emptyItem = (): ReturnTransactionItemCreate => ({
  product_id: "",
  quantity: 1,
  condition: "GOOD",
});

export const ReturnsPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ReturnTransactionCreate>({
    original_transaction_id: "",
    return_reason: "",
    returned_by: "",
    items: [emptyItem()],
  });

  const { data: returns, isLoading } = useListReturnsQuery({});
  const [createReturn, { isLoading: isCreating }] = useCreateReturnMutation();
  const [approveReturn] = useApproveReturnMutation();
  const [rejectReturn] = useRejectReturnMutation();

  const updateItem = (i: number, field: keyof ReturnTransactionItemCreate, value: unknown) =>
    setForm((f) => {
      const items = [...f.items];
      items[i] = { ...items[i], [field]: value };
      return { ...f, items };
    });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createReturn(form).unwrap();
    setShowForm(false);
    setForm({ original_transaction_id: "", return_reason: "", returned_by: "", items: [emptyItem()] });
  };

  if (isLoading) return <div className="page-container">Loading returns...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Return Transactions</h2>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Return"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>Initiate Return</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label>Original Transaction ID</label>
                <input
                  value={form.original_transaction_id}
                  onChange={(e) => setForm((f) => ({ ...f, original_transaction_id: e.target.value }))}
                  placeholder="UUID (optional)"
                />
              </div>
              <div className="form-field">
                <label>Returned By</label>
                <input
                  required
                  value={form.returned_by}
                  onChange={(e) => setForm((f) => ({ ...f, returned_by: e.target.value }))}
                />
              </div>
              <div className="form-field" style={{ gridColumn: "span 2" }}>
                <label>Return Reason</label>
                <input
                  required
                  value={form.return_reason}
                  onChange={(e) => setForm((f) => ({ ...f, return_reason: e.target.value }))}
                />
              </div>
            </div>

            <table className="items-table" style={{ marginTop: "1rem" }}>
              <thead>
                <tr>
                  <th>Product ID</th>
                  <th>Qty</th>
                  <th>Condition</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.items.map((item, i) => (
                  <tr key={i}>
                    <td>
                      <input
                        required
                        value={item.product_id}
                        onChange={(e) => updateItem(i, "product_id", e.target.value)}
                        placeholder="UUID"
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(e) => updateItem(i, "quantity", Number(e.target.value))}
                      />
                    </td>
                    <td>
                      <select
                        value={item.condition}
                        onChange={(e) => updateItem(i, "condition", e.target.value)}
                      >
                        <option value="GOOD">Good</option>
                        <option value="DAMAGED">Damaged</option>
                        <option value="FAULTY">Faulty</option>
                      </select>
                    </td>
                    <td>
                      {form.items.length > 1 && (
                        <button
                          type="button"
                          onClick={() =>
                            setForm((f) => ({ ...f, items: f.items.filter((_, j) => j !== i) }))
                          }
                        >
                          ✕
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="form-actions" style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }))}
              >
                + Add Item
              </button>
              <button type="submit" className="btn-primary" disabled={isCreating}>
                {isCreating ? "Submitting..." : "Submit Return"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Return #</th>
              <th>Original Transaction</th>
              <th>Reason</th>
              <th>Returned By</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {returns?.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-state">No returns found</td>
              </tr>
            )}
            {returns?.map((r) => (
              <tr key={r.id}>
                <td>{r.return_number}</td>
                <td className="text-muted">{r.original_transaction_id ?? "—"}</td>
                <td>{r.return_reason}</td>
                <td>{r.returned_by}</td>
                <td>
                  <span className={STATUS_BADGE[r.status] ?? "badge-draft"}>{r.status}</span>
                </td>
                <td>
                  {r.status === "PENDING" && (
                    <div className="btn-group">
                      <button className="btn-sm btn-success" onClick={() => approveReturn(r.id)}>
                        Approve
                      </button>
                      <button className="btn-sm btn-danger" onClick={() => rejectReturn(r.id)}>
                        Reject
                      </button>
                    </div>
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

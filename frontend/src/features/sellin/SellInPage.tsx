import React, { useState } from "react";
import {
  useListOrdersQuery,
  useCreateOrderMutation,
  useConfirmOrderMutation,
  useCancelOrderMutation,
  type SellInOrderCreate,
  type SellInOrderItemCreate,
} from "./sellInApi";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "badge-draft",
  CONFIRMED: "badge-warning",
  SHIPPED: "badge-warning",
  DELIVERED: "badge-confirmed",
  CANCELLED: "badge-danger",
};

const emptyItem = (): SellInOrderItemCreate => ({ product_id: "", quantity: 1, unit_cost: 0 });

export const SellInPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<SellInOrderCreate>({
    supplier_party_id: "",
    delivery_location_id: "",
    requested_delivery_date: "",
    items: [emptyItem()],
  });

  const { data, isLoading } = useListOrdersQuery({});
  const [createOrder, { isLoading: isCreating }] = useCreateOrderMutation();
  const [confirmOrder] = useConfirmOrderMutation();
  const [cancelOrder] = useCancelOrderMutation();

  const updateItem = (i: number, field: keyof SellInOrderItemCreate, value: unknown) =>
    setForm((f) => {
      const items = [...f.items];
      items[i] = { ...items[i], [field]: value };
      return { ...f, items };
    });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createOrder(form).unwrap();
    setShowForm(false);
    setForm({ supplier_party_id: "", delivery_location_id: "", requested_delivery_date: "", items: [emptyItem()] });
  };

  if (isLoading) return <div className="page-container">Loading sell-in orders...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Sell-In Orders</h2>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Order"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>Create Purchase Order</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-field">
                <label>Supplier Party ID</label>
                <input
                  required
                  value={form.supplier_party_id}
                  onChange={(e) => setForm((f) => ({ ...f, supplier_party_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div className="form-field">
                <label>Delivery Location ID</label>
                <input
                  required
                  value={form.delivery_location_id}
                  onChange={(e) => setForm((f) => ({ ...f, delivery_location_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div className="form-field">
                <label>Requested Delivery Date</label>
                <input
                  type="date"
                  required
                  value={form.requested_delivery_date}
                  onChange={(e) => setForm((f) => ({ ...f, requested_delivery_date: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Notes</label>
                <input
                  value={form.notes ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                />
              </div>
            </div>

            <table className="items-table" style={{ marginTop: "1rem" }}>
              <thead>
                <tr>
                  <th>Product ID</th>
                  <th>Qty</th>
                  <th>Unit Cost</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.items.map((item, i) => (
                  <tr key={i}>
                    <td>
                      <input required value={item.product_id} onChange={(e) => updateItem(i, "product_id", e.target.value)} placeholder="UUID" />
                    </td>
                    <td>
                      <input type="number" min={1} value={item.quantity} onChange={(e) => updateItem(i, "quantity", Number(e.target.value))} />
                    </td>
                    <td>
                      <input type="number" min={0} step="0.01" value={item.unit_cost} onChange={(e) => updateItem(i, "unit_cost", Number(e.target.value))} />
                    </td>
                    <td>
                      {form.items.length > 1 && (
                        <button type="button" onClick={() => setForm((f) => ({ ...f, items: f.items.filter((_, j) => j !== i) }))}>✕</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="form-actions" style={{ marginTop: "0.75rem" }}>
              <button type="button" onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }))}>
                + Add Item
              </button>
              <button type="submit" className="btn-primary" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Order"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Order #</th>
              <th>Supplier</th>
              <th>Delivery Date</th>
              <th>Items</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.length === 0 && (
              <tr><td colSpan={6} className="empty-state">No orders found</td></tr>
            )}
            {data?.items?.map((order) => (
              <tr key={order.id}>
                <td><strong>{order.order_number}</strong></td>
                <td className="text-mono text-muted">{order.supplier_party_id.slice(0, 8)}…</td>
                <td>{order.requested_delivery_date}</td>
                <td>{order.items?.length ?? 0}</td>
                <td><span className={STATUS_BADGE[order.status] ?? "badge-draft"}>{order.status}</span></td>
                <td>
                  <div className="btn-group">
                    {order.status === "PENDING" && (
                      <>
                        <button className="btn-sm btn-success" onClick={() => confirmOrder(order.id)}>Confirm</button>
                        <button className="btn-sm btn-danger" onClick={() => cancelOrder(order.id)}>Cancel</button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

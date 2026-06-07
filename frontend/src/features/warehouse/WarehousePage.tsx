import React, { useState } from "react";
import {
  useListBinLocationsQuery,
  useCreateBinLocationMutation,
  useListPickListsQuery,
  useCreatePickListMutation,
  useAssignPickListMutation,
  useCompletePickListMutation,
  useListPackingSlipsQuery,
  useCreatePackingSlipMutation,
  useDispatchPackingSlipMutation,
  type BinLocationCreate,
  type PickListCreate,
  type PackingSlipCreate,
} from "./warehouseApi";

type Tab = "bins" | "picklists" | "slips";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "badge-draft",
  ASSIGNED: "badge-warning",
  IN_PROGRESS: "badge-warning",
  COMPLETED: "badge-confirmed",
  CANCELLED: "badge-danger",
  PACKED: "badge-warning",
  DISPATCHED: "badge-confirmed",
  DELIVERED: "badge-confirmed",
};

// ── Bin Locations tab ─────────────────────────────────────────────────────────

const BinLocationsTab: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<BinLocationCreate>({
    location_id: "",
    zone: "",
    aisle: "",
    rack: "",
    bin: "",
  });
  const { data: bins, isLoading } = useListBinLocationsQuery({});
  const [createBin, { isLoading: isCreating }] = useCreateBinLocationMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createBin(form).unwrap();
    setShowForm(false);
    setForm({ location_id: "", zone: "", aisle: "", rack: "", bin: "" });
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <>
      <div className="tab-header">
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Bin"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Register Bin Location</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {(["location_id", "zone", "aisle", "rack", "bin"] as const).map((field) => (
                <div className="form-field" key={field}>
                  <label>{field.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}</label>
                  <input
                    required={field !== "location_id" ? undefined : true}
                    value={form[field] as string}
                    onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                    placeholder={field === "location_id" ? "Warehouse UUID" : undefined}
                  />
                </div>
              ))}
              <div className="form-field">
                <label>Capacity (optional)</label>
                <input
                  type="number"
                  min={0}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, capacity: e.target.value ? Number(e.target.value) : undefined }))
                  }
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={isCreating}>
              {isCreating ? "Creating..." : "Create Bin"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Bin Code</th>
              <th>Zone</th>
              <th>Aisle</th>
              <th>Rack</th>
              <th>Bin</th>
              <th>Capacity</th>
            </tr>
          </thead>
          <tbody>
            {bins?.length === 0 && (
              <tr><td colSpan={6} className="empty-state">No bin locations registered</td></tr>
            )}
            {bins?.map((b) => (
              <tr key={b.id}>
                <td><strong>{b.bin_code}</strong></td>
                <td>{b.zone}</td>
                <td>{b.aisle}</td>
                <td>{b.rack}</td>
                <td>{b.bin}</td>
                <td>{b.capacity ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

// ── Pick Lists tab ────────────────────────────────────────────────────────────

const PickListsTab: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [assignId, setAssignId] = useState<string | null>(null);
  const [assignee, setAssignee] = useState("");
  const [form, setForm] = useState<PickListCreate>({
    reference_order_id: "",
    order_type: "SELL_OUT",
    items: [{ product_id: "", requested_quantity: 1 }],
  });

  const { data: lists, isLoading } = useListPickListsQuery({});
  const [createList, { isLoading: isCreating }] = useCreatePickListMutation();
  const [assignList] = useAssignPickListMutation();
  const [completeList] = useCompletePickListMutation();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createList(form).unwrap();
    setShowForm(false);
    setForm({ reference_order_id: "", order_type: "SELL_OUT", items: [{ product_id: "", requested_quantity: 1 }] });
  };

  const handleAssign = async () => {
    if (!assignId || !assignee) return;
    await assignList({ id: assignId, assigned_to: assignee }).unwrap();
    setAssignId(null);
    setAssignee("");
  };

  const handleAutoComplete = async (pl: { id: string; items: Array<{ id: string; requested_quantity: number }> }) => {
    const item_picks = Object.fromEntries(pl.items.map((i) => [i.id, i.requested_quantity]));
    await completeList({ id: pl.id, item_picks }).unwrap();
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <>
      <div className="tab-header">
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Pick List"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Create Pick List</h3>
          <form onSubmit={handleCreate}>
            <div className="form-grid">
              <div className="form-field">
                <label>Reference Order ID</label>
                <input
                  required
                  value={form.reference_order_id}
                  onChange={(e) => setForm((f) => ({ ...f, reference_order_id: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Order Type</label>
                <select
                  value={form.order_type}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, order_type: e.target.value as PickListCreate["order_type"] }))
                  }
                >
                  <option value="SELL_OUT">Sell-Out</option>
                  <option value="REPLENISHMENT">Replenishment</option>
                </select>
              </div>
            </div>
            <table className="items-table" style={{ marginTop: "0.75rem" }}>
              <thead>
                <tr>
                  <th>Product ID</th>
                  <th>Qty</th>
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
                        onChange={(e) =>
                          setForm((f) => {
                            const items = [...f.items];
                            items[i] = { ...items[i], product_id: e.target.value };
                            return { ...f, items };
                          })
                        }
                        placeholder="UUID"
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.requested_quantity}
                        onChange={(e) =>
                          setForm((f) => {
                            const items = [...f.items];
                            items[i] = { ...items[i], requested_quantity: Number(e.target.value) };
                            return { ...f, items };
                          })
                        }
                      />
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
                onClick={() =>
                  setForm((f) => ({ ...f, items: [...f.items, { product_id: "", requested_quantity: 1 }] }))
                }
              >
                + Add Item
              </button>
              <button type="submit" className="btn-primary" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {assignId && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Assign Pick List</h3>
          <div className="form-row">
            <label>Assign To</label>
            <input value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="Worker ID" />
            <button className="btn-primary" onClick={handleAssign}>Assign</button>
            <button onClick={() => setAssignId(null)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Reference</th>
              <th>Type</th>
              <th>Status</th>
              <th>Assigned To</th>
              <th>Items</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {lists?.length === 0 && (
              <tr><td colSpan={7} className="empty-state">No pick lists found</td></tr>
            )}
            {lists?.map((pl) => (
              <tr key={pl.id}>
                <td>{pl.reference_order_id}</td>
                <td>{pl.order_type}</td>
                <td><span className={STATUS_BADGE[pl.status] ?? "badge-draft"}>{pl.status}</span></td>
                <td>{pl.assigned_to ?? "—"}</td>
                <td>{pl.items?.length ?? 0}</td>
                <td>{new Date(pl.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="btn-group">
                    {pl.status === "PENDING" && (
                      <button className="btn-sm" onClick={() => setAssignId(pl.id)}>Assign</button>
                    )}
                    {(pl.status === "ASSIGNED" || pl.status === "IN_PROGRESS") && (
                      <button className="btn-sm btn-success" onClick={() => handleAutoComplete(pl)}>
                        Complete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

// ── Packing Slips tab ─────────────────────────────────────────────────────────

const PackingSlipsTab: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [dispatchId, setDispatchId] = useState<string | null>(null);
  const [dispatchForm, setDispatchForm] = useState({ shipping_carrier: "", tracking_number: "" });
  const [form, setForm] = useState<PackingSlipCreate>({
    pick_list_id: "",
    packed_by: "",
    items: [{ product_id: "", quantity: 1 }],
  });

  const { data: slips, isLoading } = useListPackingSlipsQuery({});
  const [createSlip, { isLoading: isCreating }] = useCreatePackingSlipMutation();
  const [dispatch] = useDispatchPackingSlipMutation();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await createSlip(form).unwrap();
    setShowForm(false);
    setForm({ pick_list_id: "", packed_by: "", items: [{ product_id: "", quantity: 1 }] });
  };

  const handleDispatch = async () => {
    if (!dispatchId) return;
    await dispatch({ id: dispatchId, ...dispatchForm }).unwrap();
    setDispatchId(null);
    setDispatchForm({ shipping_carrier: "", tracking_number: "" });
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <>
      <div className="tab-header">
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Packing Slip"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Create Packing Slip</h3>
          <form onSubmit={handleCreate}>
            <div className="form-grid">
              <div className="form-field">
                <label>Pick List ID</label>
                <input
                  required
                  value={form.pick_list_id}
                  onChange={(e) => setForm((f) => ({ ...f, pick_list_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div className="form-field">
                <label>Packed By</label>
                <input
                  required
                  value={form.packed_by}
                  onChange={(e) => setForm((f) => ({ ...f, packed_by: e.target.value }))}
                />
              </div>
            </div>
            <table className="items-table" style={{ marginTop: "0.75rem" }}>
              <thead>
                <tr>
                  <th>Product ID</th>
                  <th>Qty</th>
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
                        onChange={(e) =>
                          setForm((f) => {
                            const items = [...f.items];
                            items[i] = { ...items[i], product_id: e.target.value };
                            return { ...f, items };
                          })
                        }
                        placeholder="UUID"
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        value={item.quantity}
                        onChange={(e) =>
                          setForm((f) => {
                            const items = [...f.items];
                            items[i] = { ...items[i], quantity: Number(e.target.value) };
                            return { ...f, items };
                          })
                        }
                      />
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
                onClick={() =>
                  setForm((f) => ({ ...f, items: [...f.items, { product_id: "", quantity: 1 }] }))
                }
              >
                + Add Item
              </button>
              <button type="submit" className="btn-primary" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Slip"}
              </button>
            </div>
          </form>
        </div>
      )}

      {dispatchId && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <h3>Dispatch Packing Slip</h3>
          <div className="form-grid">
            <div className="form-field">
              <label>Shipping Carrier</label>
              <input
                value={dispatchForm.shipping_carrier}
                onChange={(e) => setDispatchForm((f) => ({ ...f, shipping_carrier: e.target.value }))}
                placeholder="DHL, FedEx, etc."
              />
            </div>
            <div className="form-field">
              <label>Tracking Number</label>
              <input
                value={dispatchForm.tracking_number}
                onChange={(e) => setDispatchForm((f) => ({ ...f, tracking_number: e.target.value }))}
              />
            </div>
          </div>
          <div className="btn-group" style={{ marginTop: "0.75rem" }}>
            <button className="btn-primary" onClick={handleDispatch}>Dispatch</button>
            <button onClick={() => setDispatchId(null)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Slip #</th>
              <th>Pick List ID</th>
              <th>Packed By</th>
              <th>Carrier</th>
              <th>Tracking</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {slips?.length === 0 && (
              <tr><td colSpan={7} className="empty-state">No packing slips found</td></tr>
            )}
            {slips?.map((s) => (
              <tr key={s.id}>
                <td><strong>{s.slip_number}</strong></td>
                <td className="text-mono text-muted">{s.pick_list_id.slice(0, 8)}…</td>
                <td>{s.packed_by}</td>
                <td>{s.shipping_carrier ?? "—"}</td>
                <td>{s.tracking_number ?? "—"}</td>
                <td><span className={STATUS_BADGE[s.status] ?? "badge-draft"}>{s.status}</span></td>
                <td>
                  {s.status === "PACKED" && (
                    <button className="btn-sm btn-primary" onClick={() => setDispatchId(s.id)}>
                      Dispatch
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

export const WarehousePage: React.FC = () => {
  const [tab, setTab] = useState<Tab>("picklists");

  return (
    <div className="page-container">
      <h2>Warehouse Management</h2>
      <div className="tabs">
        {(["picklists", "slips", "bins"] as Tab[]).map((t) => (
          <button
            key={t}
            className={`tab-btn ${tab === t ? "tab-btn--active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t === "picklists" ? "Pick Lists" : t === "slips" ? "Packing Slips" : "Bin Locations"}
          </button>
        ))}
      </div>
      {tab === "bins" && <BinLocationsTab />}
      {tab === "picklists" && <PickListsTab />}
      {tab === "slips" && <PackingSlipsTab />}
    </div>
  );
};

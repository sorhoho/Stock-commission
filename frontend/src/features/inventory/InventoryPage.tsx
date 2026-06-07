import React, { useState } from "react";
import { useListInventoryQuery, useCreateStockTransferMutation } from "./inventoryApi";

interface StockTransferCreate {
  product_id: string;
  source_location_id: string;
  destination_location_id: string;
  quantity: number;
}

const STATUS_BADGE: Record<string, string> = {
  AVAILABLE: "badge-confirmed",
  RESERVED: "badge-draft",
  IN_TRANSIT: "badge-warning",
};

export const InventoryPage: React.FC = () => {
  const [showTransfer, setShowTransfer] = useState(false);
  const [transfer, setTransfer] = useState<StockTransferCreate>({
    product_id: "",
    source_location_id: "",
    destination_location_id: "",
    quantity: 1,
  });

  const { data: inventory, isLoading, isError } = useListInventoryQuery({});
  const [createTransfer, { isLoading: isTransferring, isSuccess: transferDone }] =
    useCreateStockTransferMutation();

  const handleTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTransfer(transfer).unwrap();
    setShowTransfer(false);
    setTransfer({ product_id: "", source_location_id: "", destination_location_id: "", quantity: 1 });
  };

  if (isLoading) return <div className="page-container">Loading inventory...</div>;
  if (isError) return <div className="page-container">Failed to load inventory.</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Product Inventory</h2>
        <button className="btn-primary" onClick={() => setShowTransfer((v) => !v)}>
          {showTransfer ? "Cancel" : "Transfer Stock"}
        </button>
      </div>

      {transferDone && (
        <div className="alert alert--success">Stock transfer created successfully.</div>
      )}

      {showTransfer && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>Create Stock Transfer</h3>
          <form onSubmit={handleTransfer}>
            <div className="form-grid">
              <div className="form-field">
                <label>Product ID</label>
                <input
                  required
                  value={transfer.product_id}
                  onChange={(e) => setTransfer((t) => ({ ...t, product_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div className="form-field">
                <label>Quantity</label>
                <input
                  type="number"
                  min={1}
                  value={transfer.quantity}
                  onChange={(e) => setTransfer((t) => ({ ...t, quantity: Number(e.target.value) }))}
                />
              </div>
              <div className="form-field">
                <label>Source Location ID</label>
                <input
                  required
                  value={transfer.source_location_id}
                  onChange={(e) => setTransfer((t) => ({ ...t, source_location_id: e.target.value }))}
                  placeholder="UUID"
                />
              </div>
              <div className="form-field">
                <label>Destination Location ID</label>
                <input
                  required
                  value={transfer.destination_location_id}
                  onChange={(e) =>
                    setTransfer((t) => ({ ...t, destination_location_id: e.target.value }))
                  }
                  placeholder="UUID"
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={isTransferring}>
              {isTransferring ? "Transferring..." : "Create Transfer"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Product ID</th>
              <th>Location</th>
              <th>Type</th>
              <th>Quantity</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {inventory?.items?.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">No inventory records found</td>
              </tr>
            )}
            {inventory?.items?.map((item) => (
              <tr key={item.id}>
                <td className="text-mono">{item.product_id}</td>
                <td className="text-mono">{item.location_id}</td>
                <td>{item.location_type}</td>
                <td>{item.quantity}</td>
                <td>
                  <span className={STATUS_BADGE[item.status] ?? "badge-draft"}>{item.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

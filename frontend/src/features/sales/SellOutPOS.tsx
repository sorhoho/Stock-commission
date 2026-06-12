import React, { useState } from "react";
import { useCreateSaleTransactionMutation } from "./salesApi";
import type { SaleTransactionCreate, SaleTransactionItemCreate } from "./salesApi";

interface Props {
  dealerPartyId: string;
}

const emptyItem = (): SaleTransactionItemCreate => ({
  product_id: "",
  product_name: "",
  quantity: 1,
  unit_price: 0,
  discount_amount: 0,
  serial_numbers: [],
  commission_eligible: true,
});

export const SellOutPOS: React.FC<Props> = ({ dealerPartyId }) => {
  const [items, setItems] = useState<SaleTransactionItemCreate[]>([emptyItem()]);
  const [channel, setChannel] = useState<SaleTransactionCreate["channel"]>("RETAIL");
  const [createTransaction, { isLoading, isSuccess, isError, data }] =
    useCreateSaleTransactionMutation();

  const totalAmount = items.reduce(
    (sum, item) => sum + (item.unit_price - (item.discount_amount ?? 0)) * item.quantity,
    0
  );

  const updateItem = (
    index: number,
    field: keyof SaleTransactionItemCreate,
    value: unknown
  ) => {
    setItems((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createTransaction({
      dealer_party_id: dealerPartyId,
      channel,
      items,
    });
  };

  return (
    <div className="pos-container">
      <h2>Point of Sale — Record Transaction</h2>

      {isSuccess && data && (
        <div className="alert alert--success">
          Transaction recorded: <strong>{data.transaction_number}</strong>
        </div>
      )}
      {isError && (
        <div className="alert alert--error">Failed to record transaction. Please retry.</div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>Channel</label>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value as SaleTransactionCreate["channel"])}
          >
            <option value="RETAIL">Retail</option>
            <option value="ONLINE">Online</option>
            <option value="AGENT">Agent</option>
            <option value="KIOSK">Kiosk</option>
          </select>
        </div>

        <table className="items-table">
          <thead>
            <tr>
              <th>Product ID</th>
              <th>Product Name</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Discount</th>
              <th>Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, idx) => (
              <tr key={idx}>
                <td>
                  <input
                    required
                    value={item.product_id}
                    onChange={(e) => updateItem(idx, "product_id", e.target.value)}
                    placeholder="UUID"
                  />
                </td>
                <td>
                  <input
                    required
                    value={item.product_name}
                    onChange={(e) => updateItem(idx, "product_name", e.target.value)}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={item.unit_price}
                    onChange={(e) => updateItem(idx, "unit_price", Number(e.target.value))}
                  />
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={item.discount_amount ?? 0}
                    onChange={(e) => updateItem(idx, "discount_amount", Number(e.target.value))}
                  />
                </td>
                <td>
                  {((item.unit_price - (item.discount_amount ?? 0)) * item.quantity).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="form-actions">
          <button type="button" onClick={() => setItems((prev) => [...prev, emptyItem()])}>
            + Add Item
          </button>
          <span className="total">Total: {totalAmount.toFixed(2)} THB</span>
          <button type="submit" disabled={isLoading} className="btn-primary">
            {isLoading ? "Processing..." : "Record Sale"}
          </button>
        </div>
      </form>
    </div>
  );
};

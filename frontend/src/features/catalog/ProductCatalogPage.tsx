import React, { useState } from "react";
import { useListProductsQuery, useCreateProductMutation, type ProductCreate } from "./catalogApi";

export const ProductCatalogPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<ProductCreate>({
    sku: "",
    name: "",
    barcode: "",
    category: "",
    unit_price: 0,
    tax_rate: 0,
  });

  const { data, isLoading } = useListProductsQuery({ search: search || undefined });
  const [createProduct, { isLoading: isCreating, isSuccess }] = useCreateProductMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createProduct(form).unwrap();
    setShowForm(false);
    setForm({ sku: "", name: "", barcode: "", category: "", unit_price: 0, tax_rate: 0 });
  };

  if (isLoading) return <div className="page-container">Loading products...</div>;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Product Catalog</h2>
        <button className="btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add Product"}
        </button>
      </div>

      {isSuccess && <div className="alert alert--success">Product created successfully.</div>}

      {showForm && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <h3>Add Product</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {(
                [
                  { key: "sku", label: "SKU" },
                  { key: "name", label: "Name" },
                  { key: "barcode", label: "Barcode" },
                  { key: "category", label: "Category" },
                ] as const
              ).map(({ key, label }) => (
                <div className="form-field" key={key}>
                  <label>{label}</label>
                  <input
                    required={key !== "barcode"}
                    value={(form[key] as string) ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  />
                </div>
              ))}
              <div className="form-field">
                <label>Unit Price</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  required
                  value={form.unit_price}
                  onChange={(e) => setForm((f) => ({ ...f, unit_price: Number(e.target.value) }))}
                />
              </div>
              <div className="form-field">
                <label>Tax Rate (%)</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step="0.01"
                  value={form.tax_rate ?? 0}
                  onChange={(e) => setForm((f) => ({ ...f, tax_rate: Number(e.target.value) }))}
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={isCreating}>
              {isCreating ? "Saving..." : "Save Product"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ marginBottom: "1rem" }}>
          <input
            className="search-input"
            placeholder="Search by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Category</th>
              <th>Barcode</th>
              <th>Unit Price</th>
              <th>Tax Rate</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.length === 0 && (
              <tr><td colSpan={6} className="empty-state">No products found</td></tr>
            )}
            {data?.items?.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.sku}</strong></td>
                <td>{p.name}</td>
                <td>{p.category}</td>
                <td className="text-mono">{p.barcode ?? "—"}</td>
                <td>{p.unit_price.toFixed(2)}</td>
                <td>{p.tax_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

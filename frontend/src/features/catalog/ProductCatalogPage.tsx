import React, { useState } from "react";
import {
  useListProductsQuery,
  useCreateProductMutation,
  PRODUCT_TYPES,
  PRODUCT_TYPE_LABELS,
  type ProductCreate,
  type ProductType,
} from "./catalogApi";

const TYPE_BADGE: Record<string, string> = {
  HANDSET: "badge-confirmed",
  TABLET: "badge-confirmed",
  SIM_CARD: "badge-paid",
  ESIM: "badge-paid",
  CASH_CARD: "badge-warning",
  SET_TOP_BOX: "badge-draft",
  OTT_TV_BOX: "badge-draft",
  CCTV: "badge-danger",
  IOT_DEVICE: "badge-danger",
  MOBILE_BROADBAND: "badge-default",
  FIXED_CPE: "badge-default",
  ACCESSORY: "badge-default",
  OTHER: "badge-default",
};

const EMPTY_FORM: ProductCreate = {
  sku: "",
  name: "",
  barcode: "",
  product_type: "HANDSET",
  category: "",
  brand: "",
  model_number: "",
  unit_price: 0,
  denomination: undefined,
  tax_rate: 0,
  commission_eligible: true,
  requires_serial_tracking: false,
  specifications: {},
};

export const ProductCatalogPage: React.FC = () => {
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<ProductType | "">("");
  const [form, setForm] = useState<ProductCreate>(EMPTY_FORM);

  const { data: products, isLoading, isError } = useListProductsQuery({
    search: search || undefined,
    product_type: typeFilter || undefined,
    size: 100,
  });
  const [createProduct, { isLoading: isCreating, isSuccess }] = useCreateProductMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createProduct(form).unwrap();
    setShowForm(false);
    setForm(EMPTY_FORM);
  };

  const set = <K extends keyof ProductCreate>(k: K, v: ProductCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Product Catalog</h2>
        {isError && <span className="alert alert--error" style={{ marginBottom: 0 }}>API unavailable — check backend</span>}
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
              <div className="form-field">
                <label>Product Type *</label>
                <select
                  required
                  value={form.product_type}
                  onChange={(e) => set("product_type", e.target.value as ProductType)}
                >
                  {PRODUCT_TYPES.map((t) => (
                    <option key={t} value={t}>{PRODUCT_TYPE_LABELS[t]}</option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label>Category *</label>
                <input
                  required
                  placeholder="HANDSET | PREPAID | TV | DATA | IOT | ACCESSORY…"
                  value={form.category}
                  onChange={(e) => set("category", e.target.value)}
                />
              </div>
              <div className="form-field">
                <label>SKU *</label>
                <input required value={form.sku} onChange={(e) => set("sku", e.target.value)} />
              </div>
              <div className="form-field">
                <label>Barcode *</label>
                <input required value={form.barcode} onChange={(e) => set("barcode", e.target.value)} placeholder="EAN-13 / internal" />
              </div>
              <div className="form-field">
                <label>Name *</label>
                <input required value={form.name} onChange={(e) => set("name", e.target.value)} />
              </div>
              <div className="form-field">
                <label>Brand</label>
                <input value={form.brand ?? ""} onChange={(e) => set("brand", e.target.value)} placeholder="Apple, Samsung, Huawei…" />
              </div>
              <div className="form-field">
                <label>Model Number</label>
                <input value={form.model_number ?? ""} onChange={(e) => set("model_number", e.target.value)} />
              </div>
              <div className="form-field">
                <label>Unit Price *</label>
                <input
                  type="number" min={0} step="0.01" required
                  value={form.unit_price}
                  onChange={(e) => set("unit_price", Number(e.target.value))}
                />
              </div>
              <div className="form-field">
                <label>Denomination (vouchers)</label>
                <input
                  type="number" min={0} step="0.01"
                  value={form.denomination ?? ""}
                  onChange={(e) => set("denomination", e.target.value ? Number(e.target.value) : undefined)}
                  placeholder="Face value for cash cards"
                />
              </div>
              <div className="form-field">
                <label>Tax Rate (0–1)</label>
                <input
                  type="number" min={0} max={1} step="0.01"
                  value={form.tax_rate ?? 0}
                  onChange={(e) => set("tax_rate", Number(e.target.value))}
                />
              </div>
            </div>
            <div className="form-row" style={{ gap: "1.5rem", marginBottom: "1rem" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", minWidth: "auto" }}>
                <input type="checkbox" checked={form.commission_eligible} onChange={(e) => set("commission_eligible", e.target.checked)} />
                Commission eligible
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", minWidth: "auto" }}>
                <input type="checkbox" checked={form.requires_serial_tracking} onChange={(e) => set("requires_serial_tracking", e.target.checked)} />
                Requires serial tracking (IMEI / ICCID)
              </label>
            </div>
            <button type="submit" className="btn-primary" disabled={isCreating}>
              {isCreating ? "Saving..." : "Save Product"}
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <div className="filter-row" style={{ marginBottom: "1rem" }}>
          <input
            className="search-input"
            placeholder="Search by name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as ProductType | "")}
            style={{ padding: "0.45rem 0.6rem", border: "1px solid #e2e8f0", borderRadius: 4, fontSize: 14 }}
          >
            <option value="">All types</option>
            {PRODUCT_TYPES.map((t) => (
              <option key={t} value={t}>{PRODUCT_TYPE_LABELS[t]}</option>
            ))}
          </select>
          {products && (
            <span className="stat-pill">{products.length} product{products.length !== 1 ? "s" : ""}</span>
          )}
        </div>

        {isLoading ? (
          <div>Loading products…</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>SKU</th>
                <th>Name / Brand</th>
                <th>Category</th>
                <th>Barcode</th>
                <th>Price</th>
                <th>Commission</th>
                <th>Serial tracked</th>
              </tr>
            </thead>
            <tbody>
              {(!products || products.length === 0) && (
                <tr><td colSpan={8} className="empty-state">No products found</td></tr>
              )}
              {products?.map((p) => (
                <tr key={p.id}>
                  <td>
                    <span className={TYPE_BADGE[p.product_type] ?? "badge-default"}>
                      {PRODUCT_TYPE_LABELS[p.product_type] ?? p.product_type}
                    </span>
                  </td>
                  <td className="text-mono">{p.sku}</td>
                  <td>
                    <strong>{p.name}</strong>
                    {p.brand && <div className="text-muted" style={{ fontSize: 12 }}>{p.brand}{p.model_number ? ` · ${p.model_number}` : ""}</div>}
                  </td>
                  <td>{p.category}</td>
                  <td className="text-mono">{p.barcode || "—"}</td>
                  <td>
                    {p.denomination != null
                      ? <span title="Face value">${p.denomination.toFixed(2)}</span>
                      : `$${p.unit_price.toFixed(2)}`}
                  </td>
                  <td>
                    <span className={p.commission_eligible ? "badge-paid" : "badge-default"}>
                      {p.commission_eligible ? "Yes" : "No"}
                    </span>
                  </td>
                  <td>
                    <span className={p.requires_serial_tracking ? "badge-confirmed" : "badge-default"}>
                      {p.requires_serial_tracking ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

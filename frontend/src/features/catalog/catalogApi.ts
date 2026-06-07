import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export const PRODUCT_TYPES = [
  "HANDSET",
  "TABLET",
  "SIM_CARD",
  "ESIM",
  "IOT_DEVICE",
  "CCTV",
  "SET_TOP_BOX",
  "OTT_TV_BOX",
  "CASH_CARD",
  "MOBILE_BROADBAND",
  "FIXED_CPE",
  "ACCESSORY",
  "OTHER",
] as const;

export type ProductType = (typeof PRODUCT_TYPES)[number];

export const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
  HANDSET: "Handset",
  TABLET: "Tablet",
  SIM_CARD: "SIM Card",
  ESIM: "eSIM",
  IOT_DEVICE: "IoT Device",
  CCTV: "CCTV",
  SET_TOP_BOX: "Set-Top Box",
  OTT_TV_BOX: "OTT TV Box",
  CASH_CARD: "Cash / Voucher Card",
  MOBILE_BROADBAND: "Mobile Broadband",
  FIXED_CPE: "Fixed CPE / Router",
  ACCESSORY: "Accessory",
  OTHER: "Other",
};

export interface ProductCreate {
  sku: string;
  name: string;
  barcode: string;
  product_type: ProductType;
  category: string;
  brand?: string;
  model_number?: string;
  unit_price: number;
  denomination?: number;
  tax_rate?: number;
  commission_eligible?: boolean;
  requires_serial_tracking?: boolean;
  specifications?: Record<string, unknown>;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  barcode: string;
  product_type: ProductType;
  category: string;
  brand: string | null;
  model_number: string | null;
  unit_price: number;
  denomination: number | null;
  tax_rate: number;
  commission_eligible: boolean;
  requires_serial_tracking: boolean;
  specifications: Record<string, unknown>;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export const catalogApi = createApi({
  reducerPath: "catalogApi",
  baseQuery,
  tagTypes: ["Product"],
  endpoints: (builder) => ({
    createProduct: builder.mutation<Product, ProductCreate>({
      query: (body) => ({ url: "/v1/productCatalog/product", method: "POST", body }),
      invalidatesTags: ["Product"],
    }),
    listProducts: builder.query<
      Product[],
      {
        barcode?: string;
        product_type?: ProductType;
        category?: string;
        brand?: string;
        search?: string;
        page?: number;
        size?: number;
      }
    >({
      query: (params) => ({ url: "/v1/productCatalog/product", params }),
      providesTags: ["Product"],
    }),
    getProduct: builder.query<Product, string>({
      query: (id) => `/v1/productCatalog/product/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Product", id }],
    }),
  }),
});

export const {
  useCreateProductMutation,
  useListProductsQuery,
  useGetProductQuery,
} = catalogApi;

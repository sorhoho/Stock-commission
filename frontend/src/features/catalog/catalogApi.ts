import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface ProductCreate {
  sku: string;
  name: string;
  barcode?: string;
  category: string;
  unit_price: number;
  tax_rate?: number;
  description?: string;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  barcode?: string;
  category: string;
  unit_price: number;
  tax_rate: number;
  description?: string;
  tenant_id: string;
  created_at: string;
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
      { items: Product[]; total: number },
      { search?: string; category?: string; page?: number; size?: number }
    >({
      query: (params) => ({ url: "/v1/productCatalog/product", params }),
      providesTags: ["Product"],
    }),
    getProductByBarcode: builder.query<Product, string>({
      query: (barcode) => ({ url: "/v1/productCatalog/product", params: { barcode } }),
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
  useGetProductByBarcodeQuery,
  useGetProductQuery,
} = catalogApi;

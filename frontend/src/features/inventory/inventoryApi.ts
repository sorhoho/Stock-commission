import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface StockAvailability {
  product_id: string;
  product_name: string;
  location_id: string;
  location_type: string;
  available_quantity: number;
  reserved_quantity: number;
  net_quantity: number;
  last_updated: string;
}

export interface ProductInventory {
  id: string;
  href: string;
  product_id: string;
  product_name: string;
  quantity: number;
  location_id: string;
  location_type: string;
  status: string;
  tenant_id: string;
  updated_at: string;
}

export interface StockTransfer {
  id: string;
  transfer_order_number: string;
  source_location_id: string;
  destination_location_id: string;
  product_id: string;
  quantity: number;
  status: string;
  requested_date: string;
  completed_date?: string;
}

export const inventoryApi = createApi({
  reducerPath: "inventoryApi",
  baseQuery,
  tagTypes: ["Inventory", "StockAvailability", "StockTransfer"],
  endpoints: (builder) => ({
    listInventory: builder.query<
      { items: ProductInventory[]; total: number },
      { location_id?: string; product_id?: string; status?: string; page?: number; size?: number }
    >({
      query: (params) => ({ url: "/v1/inventory/productInventory", params }),
      providesTags: ["Inventory"],
    }),
    queryStockAvailability: builder.query<
      StockAvailability[],
      { product_id?: string; location_id?: string; min_quantity?: number }
    >({
      query: (params) => ({ url: "/v1/inventory/stockAvailability", params }),
      providesTags: ["StockAvailability"],
    }),
    createStockTransfer: builder.mutation<StockTransfer, Partial<StockTransfer>>({
      query: (body) => ({ url: "/v1/inventory/stockTransfer", method: "POST", body }),
      invalidatesTags: ["Inventory", "StockAvailability"],
    }),
    listStockTransfers: builder.query<
      { items: StockTransfer[]; total: number },
      { status?: string; page?: number }
    >({
      query: (params) => ({ url: "/v1/inventory/stockTransfer", params }),
      providesTags: ["StockTransfer"],
    }),
  }),
});

export const {
  useListInventoryQuery,
  useQueryStockAvailabilityQuery,
  useCreateStockTransferMutation,
  useListStockTransfersQuery,
} = inventoryApi;

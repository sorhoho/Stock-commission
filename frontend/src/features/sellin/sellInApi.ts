import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface SellInOrderItemCreate {
  product_id: string;
  quantity: number;
  unit_cost: number;
}

export interface SellInOrderCreate {
  supplier_party_id: string;
  delivery_location_id: string;
  requested_delivery_date: string;
  notes?: string;
  items: SellInOrderItemCreate[];
}

export interface SellInOrderItem {
  id: string;
  product_id: string;
  quantity: number;
  delivered_quantity: number;
  unit_cost: number;
}

export interface SellInOrder {
  id: string;
  order_number: string;
  supplier_party_id: string;
  delivery_location_id: string;
  status: "PENDING" | "CONFIRMED" | "SHIPPED" | "DELIVERED" | "CANCELLED";
  requested_delivery_date: string;
  notes?: string;
  tenant_id: string;
  created_at: string;
  items: SellInOrderItem[];
}

export const sellInApi = createApi({
  reducerPath: "sellInApi",
  baseQuery,
  tagTypes: ["SellInOrder"],
  endpoints: (builder) => ({
    createOrder: builder.mutation<SellInOrder, SellInOrderCreate>({
      query: (body) => ({ url: "/v1/orderManagement/productOrder", method: "POST", body }),
      invalidatesTags: ["SellInOrder"],
    }),
    listOrders: builder.query<
      { items: SellInOrder[]; total: number },
      { status?: string; page?: number; size?: number }
    >({
      query: (params) => ({ url: "/v1/orderManagement/productOrder", params }),
      providesTags: ["SellInOrder"],
    }),
    getOrder: builder.query<SellInOrder, string>({
      query: (id) => `/v1/orderManagement/productOrder/${id}`,
      providesTags: (_r, _e, id) => [{ type: "SellInOrder", id }],
    }),
    confirmOrder: builder.mutation<SellInOrder, string>({
      query: (id) => ({ url: `/v1/orderManagement/productOrder/${id}/confirm`, method: "POST" }),
      invalidatesTags: (_r, _e, id) => [{ type: "SellInOrder", id }, "SellInOrder"],
    }),
    cancelOrder: builder.mutation<SellInOrder, string>({
      query: (id) => ({ url: `/v1/orderManagement/productOrder/${id}/cancel`, method: "POST" }),
      invalidatesTags: (_r, _e, id) => [{ type: "SellInOrder", id }, "SellInOrder"],
    }),
    markDelivered: builder.mutation<SellInOrder, { id: string; delivered_items: Record<string, number> }>({
      query: ({ id, ...body }) => ({
        url: `/v1/orderManagement/productOrder/${id}/deliver`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "SellInOrder", id }, "SellInOrder"],
    }),
  }),
});

export const {
  useCreateOrderMutation,
  useListOrdersQuery,
  useGetOrderQuery,
  useConfirmOrderMutation,
  useCancelOrderMutation,
  useMarkDeliveredMutation,
} = sellInApi;

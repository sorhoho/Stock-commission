import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

// ── Bin Location ──────────────────────────────────────────────────────────────

export interface BinLocationCreate {
  location_id: string;
  zone: string;
  aisle: string;
  rack: string;
  bin: string;
  capacity?: number;
}

export interface BinLocation {
  id: string;
  location_id: string;
  zone: string;
  aisle: string;
  rack: string;
  bin: string;
  bin_code: string;
  capacity?: number;
  tenant_id: string;
}

// ── Pick List ─────────────────────────────────────────────────────────────────

export interface PickListItemCreate {
  product_id: string;
  requested_quantity: number;
  bin_location_id?: string;
}

export interface PickListCreate {
  reference_order_id: string;
  order_type: "SELL_OUT" | "REPLENISHMENT";
  items: PickListItemCreate[];
}

export interface PickListItem {
  id: string;
  product_id: string;
  bin_location_id?: string;
  requested_quantity: number;
  picked_quantity: number;
  item_status: "PENDING" | "PICKED" | "SHORT_PICK";
}

export interface PickList {
  id: string;
  reference_order_id: string;
  order_type: string;
  status: "PENDING" | "ASSIGNED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
  assigned_to?: string;
  completed_at?: string;
  tenant_id: string;
  created_at: string;
  items: PickListItem[];
}

export interface PickListComplete {
  item_picks: Record<string, number>;
}

// ── Packing Slip ──────────────────────────────────────────────────────────────

export interface PackingSlipItemCreate {
  product_id: string;
  quantity: number;
  serial_numbers?: string[];
}

export interface PackingSlipCreate {
  pick_list_id: string;
  packed_by: string;
  items: PackingSlipItemCreate[];
}

export interface PackingSlipItem {
  id: string;
  product_id: string;
  quantity: number;
  serial_numbers: string[];
}

export interface PackingSlip {
  id: string;
  slip_number: string;
  pick_list_id: string;
  packed_by: string;
  packed_date: string;
  shipping_carrier?: string;
  tracking_number?: string;
  status: "PACKED" | "DISPATCHED" | "DELIVERED";
  tenant_id: string;
  items: PackingSlipItem[];
}

export interface DispatchRequest {
  shipping_carrier?: string;
  tracking_number?: string;
}

// ── API slice ─────────────────────────────────────────────────────────────────

export const warehouseApi = createApi({
  reducerPath: "warehouseApi",
  baseQuery,
  tagTypes: ["BinLocation", "PickList", "PackingSlip"],
  endpoints: (builder) => ({
    // Bin locations
    createBinLocation: builder.mutation<BinLocation, BinLocationCreate>({
      query: (body) => ({ url: "/v1/warehouseManagement/binLocation", method: "POST", body }),
      invalidatesTags: ["BinLocation"],
    }),
    listBinLocations: builder.query<BinLocation[], { location_id?: string; zone?: string }>({
      query: (params) => ({ url: "/v1/warehouseManagement/binLocation", params }),
      providesTags: ["BinLocation"],
    }),

    // Pick lists
    createPickList: builder.mutation<PickList, PickListCreate>({
      query: (body) => ({ url: "/v1/warehouseManagement/pickList", method: "POST", body }),
      invalidatesTags: ["PickList"],
    }),
    listPickLists: builder.query<PickList[], { status?: string; assigned_to?: string }>({
      query: (params) => ({ url: "/v1/warehouseManagement/pickList", params }),
      providesTags: ["PickList"],
    }),
    getPickList: builder.query<PickList, string>({
      query: (id) => `/v1/warehouseManagement/pickList/${id}`,
      providesTags: (_r, _e, id) => [{ type: "PickList", id }],
    }),
    assignPickList: builder.mutation<PickList, { id: string; assigned_to: string }>({
      query: ({ id, assigned_to }) => ({
        url: `/v1/warehouseManagement/pickList/${id}/assign`,
        method: "POST",
        body: { assigned_to },
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "PickList", id }, "PickList"],
    }),
    completePickList: builder.mutation<PickList, { id: string; item_picks: Record<string, number> }>({
      query: ({ id, item_picks }) => ({
        url: `/v1/warehouseManagement/pickList/${id}/complete`,
        method: "POST",
        body: { item_picks },
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "PickList", id }, "PickList"],
    }),

    // Packing slips
    createPackingSlip: builder.mutation<PackingSlip, PackingSlipCreate>({
      query: (body) => ({ url: "/v1/warehouseManagement/packingSlip", method: "POST", body }),
      invalidatesTags: ["PackingSlip"],
    }),
    getPackingSlip: builder.query<PackingSlip, string>({
      query: (id) => `/v1/warehouseManagement/packingSlip/${id}`,
      providesTags: (_r, _e, id) => [{ type: "PackingSlip", id }],
    }),
    listPackingSlips: builder.query<PackingSlip[], Record<string, never>>({
      query: () => "/v1/warehouseManagement/packingSlip",
      providesTags: ["PackingSlip"],
    }),
    dispatchPackingSlip: builder.mutation<PackingSlip, { id: string } & DispatchRequest>({
      query: ({ id, ...body }) => ({
        url: `/v1/warehouseManagement/packingSlip/${id}/dispatch`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "PackingSlip", id }, "PackingSlip"],
    }),
  }),
});

export const {
  useCreateBinLocationMutation,
  useListBinLocationsQuery,
  useCreatePickListMutation,
  useListPickListsQuery,
  useGetPickListQuery,
  useAssignPickListMutation,
  useCompletePickListMutation,
  useCreatePackingSlipMutation,
  useGetPackingSlipQuery,
  useListPackingSlipsQuery,
  useDispatchPackingSlipMutation,
} = warehouseApi;

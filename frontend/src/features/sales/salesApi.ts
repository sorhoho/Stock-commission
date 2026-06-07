import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

// ── Sale Transaction ──────────────────────────────────────────────────────────

export interface SaleTransactionItemCreate {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  discount_amount?: number;
  serial_numbers?: string[];
  commission_eligible?: boolean;
}

export interface SaleTransactionCreate {
  dealer_party_id: string;
  channel: "RETAIL" | "ONLINE" | "AGENT" | "KIOSK";
  items: SaleTransactionItemCreate[];
  pos_session_id?: string;
  payment_method?: "CASH" | "CARD" | "MOBILE_MONEY" | "CREDIT";
  payment_reference?: string;
  sale_date?: string;
}

export interface SaleTransaction {
  id: string;
  transaction_number: string;
  dealer_party_id: string;
  channel: string;
  total_amount: number;
  currency: string;
  status: string;
  pos_session_id?: string;
  payment_method?: string;
  payment_reference?: string;
  tenant_id: string;
  created_at: string;
}

export interface SaleTransactionSummary {
  dealer_party_id: string;
  period: string;
  total_transactions: number;
  total_units: number;
  total_amount: number;
  currency: string;
}

// ── POS Session ───────────────────────────────────────────────────────────────

export interface PosSessionCreate {
  terminal_id: string;
  dealer_party_id: string;
  opened_by: string;
  opening_cash: number;
}

export interface PosSessionClose {
  closing_cash: number;
}

export interface PosSession {
  id: string;
  terminal_id: string;
  dealer_party_id: string;
  opened_by: string;
  status: "OPEN" | "CLOSED";
  opening_cash: number;
  closing_cash?: number;
  total_transactions: number;
  total_amount: number;
  tenant_id: string;
  created_at: string;
  closed_at?: string;
}

// ── Return Transaction ────────────────────────────────────────────────────────

export interface ReturnTransactionItemCreate {
  product_id: string;
  quantity: number;
  serial_numbers?: string[];
  condition: "GOOD" | "DAMAGED" | "FAULTY";
}

export interface ReturnTransactionCreate {
  original_transaction_id?: string;
  return_reason: string;
  returned_by: string;
  items: ReturnTransactionItemCreate[];
}

export interface ReturnTransaction {
  id: string;
  return_number: string;
  original_transaction_id?: string;
  return_reason: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  returned_by: string;
  tenant_id: string;
  created_at: string;
}

// ── API slice ─────────────────────────────────────────────────────────────────

export const salesApi = createApi({
  reducerPath: "salesApi",
  baseQuery,
  tagTypes: ["SaleTransaction", "PosSession", "ReturnTransaction"],
  endpoints: (builder) => ({
    // Sale transactions
    createSaleTransaction: builder.mutation<SaleTransaction, SaleTransactionCreate>({
      query: (body) => ({ url: "/v1/salesManagement/saleTransaction", method: "POST", body }),
      invalidatesTags: ["SaleTransaction"],
    }),
    listSaleTransactions: builder.query<
      { items: SaleTransaction[]; total: number },
      { dealer_party_id?: string; from_date?: string; to_date?: string; page?: number; size?: number }
    >({
      query: (params) => ({ url: "/v1/salesManagement/saleTransaction", params }),
      providesTags: ["SaleTransaction"],
    }),
    getSaleTransaction: builder.query<SaleTransaction, string>({
      query: (id) => `/v1/salesManagement/saleTransaction/${id}`,
      providesTags: (_r, _e, id) => [{ type: "SaleTransaction", id }],
    }),
    getSaleTransactionSummary: builder.query<
      SaleTransactionSummary,
      { dealer_party_id: string; period: string }
    >({
      query: (params) => ({ url: "/v1/salesManagement/saleTransaction/summary", params }),
    }),

    // POS sessions
    openPosSession: builder.mutation<PosSession, PosSessionCreate>({
      query: (body) => ({ url: "/v1/salesManagement/posSession", method: "POST", body }),
      invalidatesTags: ["PosSession"],
    }),
    getPosSession: builder.query<PosSession, string>({
      query: (id) => `/v1/salesManagement/posSession/${id}`,
      providesTags: (_r, _e, id) => [{ type: "PosSession", id }],
    }),
    closePosSession: builder.mutation<PosSession, { id: string; body: PosSessionClose }>({
      query: ({ id, body }) => ({
        url: `/v1/salesManagement/posSession/${id}/close`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_r, _e, { id }) => [{ type: "PosSession", id }],
    }),

    // Return transactions
    createReturn: builder.mutation<ReturnTransaction, ReturnTransactionCreate>({
      query: (body) => ({ url: "/v1/salesManagement/returnTransaction", method: "POST", body }),
      invalidatesTags: ["ReturnTransaction"],
    }),
    listReturns: builder.query<ReturnTransaction[], { page?: number; size?: number }>({
      query: (params) => ({ url: "/v1/salesManagement/returnTransaction", params }),
      providesTags: ["ReturnTransaction"],
    }),
    approveReturn: builder.mutation<ReturnTransaction, string>({
      query: (id) => ({ url: `/v1/salesManagement/returnTransaction/${id}/approve`, method: "POST" }),
      invalidatesTags: ["ReturnTransaction"],
    }),
    rejectReturn: builder.mutation<ReturnTransaction, string>({
      query: (id) => ({ url: `/v1/salesManagement/returnTransaction/${id}/reject`, method: "POST" }),
      invalidatesTags: ["ReturnTransaction"],
    }),
  }),
});

export const {
  useCreateSaleTransactionMutation,
  useListSaleTransactionsQuery,
  useGetSaleTransactionQuery,
  useGetSaleTransactionSummaryQuery,
  useOpenPosSessionMutation,
  useGetPosSessionQuery,
  useClosePosSessionMutation,
  useCreateReturnMutation,
  useListReturnsQuery,
  useApproveReturnMutation,
  useRejectReturnMutation,
} = salesApi;

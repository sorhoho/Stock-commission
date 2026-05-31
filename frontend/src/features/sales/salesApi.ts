import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

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

export const salesApi = createApi({
  reducerPath: "salesApi",
  baseQuery,
  tagTypes: ["SaleTransaction"],
  endpoints: (builder) => ({
    createSaleTransaction: builder.mutation<SaleTransaction, SaleTransactionCreate>({
      query: (body) => ({
        url: "/v1/salesManagement/saleTransaction",
        method: "POST",
        body,
      }),
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
      providesTags: (_result, _error, id) => [{ type: "SaleTransaction", id }],
    }),
    getSaleTransactionSummary: builder.query<
      SaleTransactionSummary,
      { dealer_party_id: string; period: string }
    >({
      query: (params) => ({ url: "/v1/salesManagement/saleTransaction/summary", params }),
    }),
  }),
});

export const {
  useCreateSaleTransactionMutation,
  useListSaleTransactionsQuery,
  useGetSaleTransactionQuery,
  useGetSaleTransactionSummaryQuery,
} = salesApi;

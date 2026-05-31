import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface CommissionEvent {
  id: string;
  source_transaction_id: string;
  party_id: string;
  agreement_id: string;
  commission_amount: number;
  currency: string;
  calculation_date: string;
  status: string;
}

export interface CommissionStatement {
  id: string;
  party_id: string;
  period_year: number;
  period_month: number;
  total_commission: number;
  currency: string;
  line_items_count: number;
  status: "DRAFT" | "CONFIRMED" | "PAID";
  confirmed_at?: string;
}

export interface PayoutRequest {
  id: string;
  party_id: string;
  statement_id: string;
  amount: number;
  currency: string;
  status: string;
  scheduled_date: string;
  processed_date?: string;
}

export const commissionApi = createApi({
  reducerPath: "commissionApi",
  baseQuery,
  tagTypes: ["CommissionEvent", "CommissionStatement", "PayoutRequest"],
  endpoints: (builder) => ({
    listCommissionEvents: builder.query<
      { items: CommissionEvent[]; total: number },
      { party_id?: string; from_date?: string; to_date?: string; status?: string; page?: number }
    >({
      query: (params) => ({ url: "/v1/accountManagement/commissionEvent", params }),
      providesTags: ["CommissionEvent"],
    }),
    listCommissionStatements: builder.query<
      CommissionStatement[],
      { party_id?: string; year?: number; month?: number }
    >({
      query: (params) => ({ url: "/v1/accountManagement/commissionStatement", params }),
      providesTags: ["CommissionStatement"],
    }),
    getCommissionStatement: builder.query<CommissionStatement, string>({
      query: (id) => `/v1/accountManagement/commissionStatement/${id}`,
      providesTags: (_result, _error, id) => [{ type: "CommissionStatement", id }],
    }),
    confirmStatement: builder.mutation<CommissionStatement, string>({
      query: (id) => ({ url: `/v1/accountManagement/commissionStatement/${id}/confirm`, method: "POST" }),
      invalidatesTags: ["CommissionStatement"],
    }),
    listPayoutRequests: builder.query<
      PayoutRequest[],
      { party_id?: string; status?: string }
    >({
      query: (params) => ({ url: "/v1/payout/payoutRequest", params }),
      providesTags: ["PayoutRequest"],
    }),
  }),
});

export const {
  useListCommissionEventsQuery,
  useListCommissionStatementsQuery,
  useGetCommissionStatementQuery,
  useConfirmStatementMutation,
  useListPayoutRequestsQuery,
} = commissionApi;

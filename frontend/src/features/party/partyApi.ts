import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface PartyCreate {
  name: string;
  party_type: "DEALER" | "DISTRIBUTOR" | "EMPLOYEE" | "CUSTOMER";
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  parent_party_id?: string;
}

export interface Party {
  id: string;
  name: string;
  party_type: string;
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  parent_party_id?: string;
  status: "ACTIVE" | "INACTIVE" | "SUSPENDED";
  tenant_id: string;
  created_at: string;
}

export const partyApi = createApi({
  reducerPath: "partyApi",
  baseQuery,
  tagTypes: ["Party"],
  endpoints: (builder) => ({
    createParty: builder.mutation<Party, PartyCreate>({
      query: (body) => ({ url: "/v1/partyManagement/party", method: "POST", body }),
      invalidatesTags: ["Party"],
    }),
    listParties: builder.query<
      { items: Party[]; total: number },
      { party_type?: string; status?: string; page?: number; size?: number }
    >({
      query: (params) => ({ url: "/v1/partyManagement/party", params }),
      providesTags: ["Party"],
    }),
    getParty: builder.query<Party, string>({
      query: (id) => `/v1/partyManagement/party/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Party", id }],
    }),
  }),
});

export const { useCreatePartyMutation, useListPartiesQuery, useGetPartyQuery } = partyApi;

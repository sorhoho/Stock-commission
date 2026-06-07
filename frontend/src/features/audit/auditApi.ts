import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface AuditLog {
  id: string;
  event_type: string;
  source_service: string;
  entity_type: string;
  entity_id: string;
  actor: string;
  payload: Record<string, unknown>;
  tenant_id: string;
  created_at: string;
}

export const auditApi = createApi({
  reducerPath: "auditApi",
  baseQuery,
  tagTypes: ["AuditLog"],
  endpoints: (builder) => ({
    listAuditLogs: builder.query<
      { items: AuditLog[]; total: number },
      {
        event_type?: string;
        source_service?: string;
        entity_type?: string;
        entity_id?: string;
        from_date?: string;
        to_date?: string;
        page?: number;
        size?: number;
      }
    >({
      query: (params) => ({ url: "/v1/auditLog/entry", params }),
      providesTags: ["AuditLog"],
    }),
  }),
});

export const { useListAuditLogsQuery } = auditApi;

import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "../../shared/api/apiClient";

export interface PerformanceTarget {
  id: string;
  party_id: string;
  kpi_spec_id: string;
  target_value: number;
  period_start: string;
  period_end: string;
  status: "ACTIVE" | "ACHIEVED" | "MISSED";
}

export interface PerformanceMeasurement {
  id: string;
  party_id: string;
  kpi_spec_id: string;
  period: string;
  measured_value: number;
  created_at: string;
}

export interface PerformanceDashboard {
  party_id: string;
  period: string;
  measurements: PerformanceMeasurement[];
  targets: PerformanceTarget[];
  summary: Record<string, { target: number; actual: number; variance: number; achieved: boolean }>;
}

export const performanceApi = createApi({
  reducerPath: "performanceApi",
  baseQuery,
  tagTypes: ["PerformanceDashboard", "PerformanceTarget", "PerformanceMeasurement"],
  endpoints: (builder) => ({
    getPerformanceDashboard: builder.query<
      PerformanceDashboard,
      { party_id: string; period: string }
    >({
      query: (params) => ({ url: "/v1/performanceManagement/performanceDashboard", params }),
      providesTags: ["PerformanceDashboard"],
    }),
    listTargets: builder.query<
      PerformanceTarget[],
      { party_id?: string; kpi_spec_id?: string; period?: string }
    >({
      query: (params) => ({ url: "/v1/performanceManagement/performanceTarget", params }),
      providesTags: ["PerformanceTarget"],
    }),
    listMeasurements: builder.query<
      PerformanceMeasurement[],
      { party_id?: string; kpi_spec_id?: string; from_date?: string; to_date?: string }
    >({
      query: (params) => ({ url: "/v1/performanceManagement/performanceMeasurement", params }),
      providesTags: ["PerformanceMeasurement"],
    }),
  }),
});

export const {
  useGetPerformanceDashboardQuery,
  useListTargetsQuery,
  useListMeasurementsQuery,
} = performanceApi;

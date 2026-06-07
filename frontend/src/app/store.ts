import { configureStore } from "@reduxjs/toolkit";
import { inventoryApi } from "../features/inventory/inventoryApi";
import { salesApi } from "../features/sales/salesApi";
import { performanceApi } from "../features/performance/performanceApi";
import { commissionApi } from "../features/commission/commissionApi";
import { warehouseApi } from "../features/warehouse/warehouseApi";
import { sellInApi } from "../features/sellin/sellInApi";
import { catalogApi } from "../features/catalog/catalogApi";
import { partyApi } from "../features/party/partyApi";
import { auditApi } from "../features/audit/auditApi";
import authReducer from "./authSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    [inventoryApi.reducerPath]: inventoryApi.reducer,
    [salesApi.reducerPath]: salesApi.reducer,
    [performanceApi.reducerPath]: performanceApi.reducer,
    [commissionApi.reducerPath]: commissionApi.reducer,
    [warehouseApi.reducerPath]: warehouseApi.reducer,
    [sellInApi.reducerPath]: sellInApi.reducer,
    [catalogApi.reducerPath]: catalogApi.reducer,
    [partyApi.reducerPath]: partyApi.reducer,
    [auditApi.reducerPath]: auditApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(inventoryApi.middleware)
      .concat(salesApi.middleware)
      .concat(performanceApi.middleware)
      .concat(commissionApi.middleware)
      .concat(warehouseApi.middleware)
      .concat(sellInApi.middleware)
      .concat(catalogApi.middleware)
      .concat(partyApi.middleware)
      .concat(auditApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

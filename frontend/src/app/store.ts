import { configureStore } from "@reduxjs/toolkit";
import { inventoryApi } from "../features/inventory/inventoryApi";
import { salesApi } from "../features/sales/salesApi";
import { performanceApi } from "../features/performance/performanceApi";
import { commissionApi } from "../features/commission/commissionApi";
import authReducer from "./authSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    [inventoryApi.reducerPath]: inventoryApi.reducer,
    [salesApi.reducerPath]: salesApi.reducer,
    [performanceApi.reducerPath]: performanceApi.reducer,
    [commissionApi.reducerPath]: commissionApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(inventoryApi.middleware)
      .concat(salesApi.middleware)
      .concat(performanceApi.middleware)
      .concat(commissionApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

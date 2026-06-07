import React from "react";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { Layout } from "../shared/components/Layout";
import { SellOutPOS } from "../features/sales/SellOutPOS";
import { PosSessionPage } from "../features/sales/PosSessionPage";
import { ReturnsPage } from "../features/sales/ReturnsPage";
import { InventoryPage } from "../features/inventory/InventoryPage";
import { WarehousePage } from "../features/warehouse/WarehousePage";
import { SellInPage } from "../features/sellin/SellInPage";
import { ProductCatalogPage } from "../features/catalog/ProductCatalogPage";
import { PartiesPage } from "../features/party/PartiesPage";
import { CommissionRulesPage } from "../features/commission/CommissionRulesPage";
import { CommissionStatement } from "../features/commission/CommissionStatement";
import { PayoutPage } from "../features/payout/PayoutPage";
import { KPIDashboard } from "../features/performance/KPIDashboard";
import { AuditPage } from "../features/audit/AuditPage";

const DEMO_PARTY_ID = "00000000-0000-0000-0000-000000000001";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/sales/pos" replace /> },
      { path: "sales/pos", element: <SellOutPOS dealerPartyId={DEMO_PARTY_ID} /> },
      { path: "sales/sessions", element: <PosSessionPage /> },
      { path: "sales/returns", element: <ReturnsPage /> },
      { path: "inventory", element: <InventoryPage /> },
      { path: "warehouse", element: <WarehousePage /> },
      { path: "sellin", element: <SellInPage /> },
      { path: "catalog", element: <ProductCatalogPage /> },
      { path: "parties", element: <PartiesPage /> },
      { path: "commission/rules", element: <CommissionRulesPage /> },
      { path: "commission/statements", element: <CommissionStatement partyId={DEMO_PARTY_ID} /> },
      { path: "payouts", element: <PayoutPage /> },
      { path: "performance", element: <KPIDashboard partyId={DEMO_PARTY_ID} /> },
      { path: "audit", element: <AuditPage /> },
    ],
  },
]);

export const AppRouter: React.FC = () => <RouterProvider router={router} />;

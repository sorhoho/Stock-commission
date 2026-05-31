import React from "react";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { SellOutPOS } from "../features/sales/SellOutPOS";
import { KPIDashboard } from "../features/performance/KPIDashboard";
import { CommissionStatement } from "../features/commission/CommissionStatement";

const DEMO_PARTY_ID = "00000000-0000-0000-0000-000000000001";

const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/sales/pos" replace /> },
  {
    path: "/sales/pos",
    element: <SellOutPOS dealerPartyId={DEMO_PARTY_ID} />,
  },
  {
    path: "/performance",
    element: <KPIDashboard partyId={DEMO_PARTY_ID} />,
  },
  {
    path: "/commission/statements",
    element: <CommissionStatement partyId={DEMO_PARTY_ID} />,
  },
]);

export const AppRouter: React.FC = () => <RouterProvider router={router} />;

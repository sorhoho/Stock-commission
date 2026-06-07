import React, { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { label: "POS / Sell-Out", path: "/sales/pos", icon: "🛒" },
  { label: "POS Sessions", path: "/sales/sessions", icon: "🖥️" },
  { label: "Returns", path: "/sales/returns", icon: "↩️" },
  { label: "Sell-In Orders", path: "/sellin", icon: "📦" },
  { label: "Inventory", path: "/inventory", icon: "🗄️" },
  { label: "Warehouse", path: "/warehouse", icon: "🏭" },
  { label: "Product Catalog", path: "/catalog", icon: "📋" },
  { label: "Parties / Dealers", path: "/parties", icon: "👥" },
  { label: "Commission Rules", path: "/commission/rules", icon: "📜" },
  { label: "Commission Statements", path: "/commission/statements", icon: "💰" },
  { label: "Payouts", path: "/payouts", icon: "💳" },
  { label: "Performance", path: "/performance", icon: "📈" },
  { label: "Audit Log", path: "/audit", icon: "🔍" },
];

export const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`app-layout ${collapsed ? "app-layout--collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-logo">Telco DMS</span>
          <button className="sidebar-toggle" onClick={() => setCollapsed((c) => !c)}>
            {collapsed ? "▶" : "◀"}
          </button>
        </div>
        <nav>
          {NAV.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}
            >
              <span className="nav-icon">{item.icon}</span>
              {!collapsed && <span className="nav-label">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
};

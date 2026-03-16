import { Cable, ChartColumn, CirclePower, FileCode2, LayoutDashboard, Ticket } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { StatusWidget } from "@/components/StatusWidget";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testid: "nav-dashboard-link" },
  { to: "/vouchers", label: "Vouchers", icon: Ticket, testid: "nav-vouchers-link" },
  { to: "/vlans", label: "Sub-Vendo VLAN", icon: Cable, testid: "nav-vlans-link" },
  { to: "/gpio", label: "GPIO & Relay", icon: CirclePower, testid: "nav-gpio-link" },
  { to: "/reports", label: "Sales Reports", icon: ChartColumn, testid: "nav-reports-link" },
  { to: "/config", label: "Config Export", icon: FileCode2, testid: "nav-config-link" },
];

export const AppLayout = () => {
  return (
    <div className="app-shell min-h-screen flex" data-testid="app-shell">
      <aside className="hidden md:flex md:w-64 border-r bg-card p-4 flex-col gap-4 sticky top-0 h-screen" data-testid="sidebar-navigation">
        <div className="rounded-lg border bg-background p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground" data-testid="brand-caption">
            PisoFi Commander
          </p>
          <h1 className="mt-2 text-xl font-semibold" data-testid="brand-title">Vendo Control</h1>
        </div>
        <nav className="flex-1 space-y-1" data-testid="main-navigation-list">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={item.testid}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-primary text-primary-foreground" : "hover:bg-secondary text-foreground"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 w-full overflow-x-hidden" data-testid="main-content-area">
        <header className="border-b bg-card p-4 md:p-6" data-testid="top-header">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground" data-testid="header-subtitle">
                Lightweight Linux Vendo Controller
              </p>
              <h2 className="text-2xl font-medium tracking-tight" data-testid="header-title">
                PISO WiFi Operations Panel
              </h2>
            </div>
            <StatusWidget />
          </div>
        </header>
        <section className="p-4 md:p-8" data-testid="page-content-wrapper">
          <Outlet />
        </section>
      </main>
    </div>
  );
};

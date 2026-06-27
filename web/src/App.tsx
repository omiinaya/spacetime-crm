import { useState, useEffect } from "react";
import { Toaster } from "sonner";
import {
  LayoutDashboard, Users, Ticket, FileText, CreditCard,
  Calendar, Package, FileCheck, ShoppingCart, Settings,
  Menu, Users as UsersIcon,
} from "lucide-react";
import { cn } from "./lib/utils";
import { api, DashboardStats } from "./lib/api";
import { Badge } from "./components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { AuthProvider, useAuth } from "./lib/auth";
import LoginPage from "./pages/LoginPage";
import CustomersPage from "./pages/CustomersPage";
import TicketsPage from "./pages/TicketsPage";
import InvoicesPage from "./pages/InvoicesPage";
import PaymentsPage from "./pages/PaymentsPage";
import AppointmentsPage from "./pages/AppointmentsPage";
import ProductsPage from "./pages/ProductsPage";
import EstimatesPage from "./pages/EstimatesPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import SettingsPage from "./pages/SettingsPage";

type PageId =
  | "dashboard" | "customers" | "tickets" | "invoices"
  | "payments" | "appointments" | "products" | "estimates"
  | "purchase-orders" | "settings";

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: () => number;
}

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "customers", label: "Customers", icon: Users },
  { id: "tickets", label: "Tickets", icon: Ticket },
  { id: "invoices", label: "Invoices", icon: FileText },
  { id: "payments", label: "Payments", icon: CreditCard },
  { id: "appointments", label: "Appointments", icon: Calendar },
  { id: "products", label: "Products", icon: Package },
  { id: "estimates", label: "Estimates", icon: FileCheck },
  { id: "purchase-orders", label: "Purchase Orders", icon: ShoppingCart },
  { id: "settings", label: "Settings", icon: Settings },
];

function AppShell() {
  const { user, logout, loading } = useAuth();
  const [page, setPage] = useState<PageId>("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    if (user) {
      api.stats.get().then(setStats).catch(() => {});
    }
  }, [page, user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const renderPage = () => {
    switch (page) {
      case "dashboard":
        return <DashboardPage stats={stats} onNavigate={setPage} />;
      case "customers":
        return <CustomersPage />;
      case "tickets":
        return <TicketsPage />;
      case "invoices":
        return <InvoicesPage />;
      case "payments":
        return <PaymentsPage />;
      case "appointments":
        return <AppointmentsPage />;
      case "products":
        return <ProductsPage />;
      case "estimates":
        return <EstimatesPage />;
      case "purchase-orders":
        return <PurchaseOrdersPage />;
      case "settings":
        return <SettingsPage />;
    }
  };

  const sidebar = (
    <nav className="flex flex-col h-full">
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 h-14 border-b border-border shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
          <UsersIcon className="h-4 w-4 text-white" />
        </div>
        <span className="font-semibold text-sm">SpacetimeCRM</span>
      </div>

      {/* User info */}
      <div className="px-4 py-3 border-b border-border shrink-0">
        <p className="text-sm font-medium">{user.name}</p>
        <p className="text-xs text-muted-foreground">{user.role}</p>
      </div>

      {/* Nav items */}
      <div className="flex-1 overflow-y-auto py-2 space-y-1 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => {
                setPage(item.id);
                setMobileOpen(false);
              }}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors border-l-2",
                page === item.id
                  ? "bg-primary/10 text-foreground font-medium border-l-2 border-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted border-l-2 border-transparent"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Logout */}
      <div className="p-2 border-t border-border">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="truncate">Sign out</span>
        </button>
      </div>
    </nav>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed md:relative z-50 md:z-0 w-64 h-full bg-[var(--color-sidebar)] border-r border-border transition-transform md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {sidebar}
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="md:hidden flex items-center gap-3 px-4 h-12 border-b border-border shrink-0">
          <button onClick={() => setMobileOpen(true)}>
            <Menu className="h-5 w-5" />
          </button>
          <span className="font-semibold text-sm">SpacetimeCRM</span>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 space-y-6">
          {renderPage()}
        </div>
      </main>

      <Toaster position="bottom-left" theme="dark" />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

function DashboardPage({
  stats,
  onNavigate,
}: {
  stats: DashboardStats | null;
  onNavigate: (p: PageId) => void;
}) {
  const summaryCards = [
    {
      label: "Total Customers",
      value: stats?.total_customers ?? 0,
      icon: Users,
      color: "text-blue-400",
      link: "customers" as PageId,
    },
    {
      label: "Open Tickets",
      value: stats?.open_tickets ?? 0,
      icon: Ticket,
      color: "text-amber-400",
      link: "tickets" as PageId,
    },
    {
      label: "Revenue",
      value: `$${(stats?.revenue ?? 0).toFixed(2)}`,
      icon: CreditCard,
      color: "text-green-400",
      link: "invoices" as PageId,
    },
    {
      label: "Upcoming Appointments",
      value: stats?.upcoming_appointments ?? 0,
      icon: Calendar,
      color: "text-purple-400",
      link: "appointments" as PageId,
    },
  ];

  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Overview of your repair business
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card
              key={card.label}
              className="cursor-pointer hover:bg-[var(--color-card)]/80 transition-colors"
              onClick={() => onNavigate(card.link)}
            >
              <CardContent className="flex items-center gap-4 pt-4">
                <div className="p-2 rounded-lg bg-muted">
                  <Icon className={`h-5 w-5 ${card.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-muted-foreground">{card.label}</p>
                  <p className="text-xl font-bold">{card.value}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {[
            { label: "New Customer", page: "customers" as PageId, icon: Users },
            { label: "New Ticket", page: "tickets" as PageId, icon: Ticket },
            { label: "New Invoice", page: "invoices" as PageId, icon: FileText },
            { label: "New Appointment", page: "appointments" as PageId, icon: Calendar },
            { label: "Add Product", page: "products" as PageId, icon: Package },
          ].map((action) => {
            const Icon = action.icon;
            return (
              <Button
                key={action.label}
                variant="outline"
                className="h-20 flex-col gap-2"
                onClick={() => onNavigate(action.page)}
              >
                <Icon className="h-5 w-5" />
                <span className="text-xs">{action.label}</span>
              </Button>
            );
          })}
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Open tickets:{" "}
              <span className="text-foreground font-medium">{stats?.open_tickets ?? 0}</span>
            </p>
            <p className="text-sm text-muted-foreground">
              Pending revenue:{" "}
              <span className="text-foreground font-medium">
                ${(stats?.pending_revenue ?? 0).toFixed(2)}
              </span>
            </p>
            <p className="text-sm text-muted-foreground">
              Total customers:{" "}
              <span className="text-foreground font-medium">{stats?.total_customers ?? 0}</span>
            </p>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

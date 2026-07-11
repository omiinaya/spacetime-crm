import { useState, useEffect, Suspense, lazy } from "react";
import { Toaster } from "sonner";
import {
  LayoutDashboard, Users, Ticket, FileText, CreditCard,
  Calendar, Package, FileCheck, ShoppingCart, BarChart3, Settings,
  Menu, Users as UsersIcon, LogOut, ExternalLink, Sun, Moon,
  Download, Upload, History, HeartPulse, ListOrdered, Map, ListChecks,
  Building2, Repeat,
} from "lucide-react";
import { cn } from "./lib/utils";
import { api, DashboardStats } from "./lib/api";
import { Badge } from "./components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { AuthProvider, useAuth, hasRole } from "./lib/auth";
import { PortalAuthProvider, usePortalAuth } from "./lib/portal-auth";
import { useTheme } from "./lib/theme";
import ErrorBoundary from "./components/ErrorBoundary";
import { QueryProvider } from "./lib/query-client";
const LoginPage = lazy(() => import("./pages/LoginPage"));
const ForgotPasswordPage = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const PortalLoginPage = lazy(() => import("./pages/PortalLoginPage"));
const PortalDashboard = lazy(() => import("./pages/PortalDashboard"));
const PortalTicketsPage = lazy(() => import("./pages/PortalTicketsPage"));
const PortalInvoicesPage = lazy(() => import("./pages/PortalInvoicesPage"));
const PortalAppointmentsPage = lazy(() => import("./pages/PortalAppointmentsPage"));
const CustomersPage = lazy(() => import("./pages/CustomersPage"));
const TicketsPage = lazy(() => import("./pages/TicketsPage"));
const InvoicesPage = lazy(() => import("./pages/InvoicesPage"));
const PaymentsPage = lazy(() => import("./pages/PaymentsPage"));
const AppointmentsPage = lazy(() => import("./pages/AppointmentsPage"));
const ProductsPage = lazy(() => import("./pages/ProductsPage"));
const EstimatesPage = lazy(() => import("./pages/EstimatesPage"));
const PurchaseOrdersPage = lazy(() => import("./pages/PurchaseOrdersPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const ImportExportPage = lazy(() => import("./pages/ImportExportPage"));
const AuditLogPage = lazy(() => import("./pages/AuditLogPage"));
const HealthPage = lazy(() => import("./pages/HealthPage"));
const CustomFieldsPage = lazy(() => import("./pages/CustomFieldsPage"));
const MapPage = lazy(() => import("./pages/MapPage"));
const ChecklistTemplatesPage = lazy(() => import("./pages/ChecklistTemplatesPage"));
const TenantsPage = lazy(() => import("./pages/TenantsPage"));
const RecurringInvoicesPage = lazy(() => import("./pages/RecurringInvoicesPage"));
const PaymentMethodsPage = lazy(() => import("./pages/PaymentMethodsPage"));
const PosPage = lazy(() => import("./pages/PosPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));

type PageId =
  | "dashboard" | "customers" | "tickets" | "invoices"
  | "payments" | "appointments" | "products" | "estimates"
  | "purchase-orders" | "import-export" | "audit-log" | "pos"
  | "health" | "custom-fields" | "checklist" | "map" | "reports" | "settings" | "tenants"
  | "recurring-invoices" | "payment-methods";

type PortalPage = "dashboard" | "tickets" | "invoices" | "appointments";

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ComponentType<any>;
  badge?: () => number;
}

const navItems: { id: PageId; label: string; icon: React.ComponentType<any>; badge?: () => number; }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "customers", label: "Customers", icon: Users },
  { id: "map", label: "Map", icon: Map },
  { id: "tickets", label: "Tickets", icon: Ticket },
  { id: "invoices", label: "Invoices", icon: FileText },
  { id: "recurring-invoices", label: "Recurring", icon: Repeat },
  { id: "payments", label: "Payments", icon: CreditCard },
  { id: "payment-methods", label: "Payment Methods", icon: CreditCard },
  { id: "appointments", label: "Appointments", icon: Calendar },
  { id: "products", label: "Products", icon: Package },
  { id: "estimates", label: "Estimates", icon: FileCheck },
  { id: "purchase-orders", label: "Purchase Orders", icon: ShoppingCart },
  { id: "pos", label: "POS", icon: CreditCard },
  { id: "import-export", label: "Import/Export", icon: Download },
  { id: "custom-fields", label: "Custom Fields", icon: ListOrdered },
  { id: "checklist", label: "Checklists", icon: ListChecks },
  { id: "health", label: "Health", icon: HeartPulse },
  { id: "audit-log", label: "Audit Log", icon: History },
  { id: "reports", label: "Reports", icon: BarChart3 },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "tenants", label: "Tenants", icon: Building2 },
];

// ── Portal App ──

const portalTabs: { id: PortalPage; label: string; icon: React.ComponentType<any> }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "tickets", label: "Tickets", icon: Ticket },
  { id: "invoices", label: "Invoices", icon: FileText },
  { id: "appointments", label: "Appointments", icon: Calendar },
];

function PortalShell() {
  const { customer, logout, loading } = usePortalAuth();
  const [page, setPage] = useState<PortalPage>("dashboard");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!customer) {
    return <PortalLoginPage onSuccess={() => window.location.reload()} />;
  }

  const renderPortalPage = () => {
    return (
      <ErrorBoundary>
        <Suspense fallback={<div className="flex items-center justify-center py-20"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>}>
          {(() => {
          switch (page) {
            case "dashboard": return <ErrorBoundary><PortalDashboard /></ErrorBoundary>;
            case "tickets": return <ErrorBoundary><PortalTicketsPage /></ErrorBoundary>;
            case "invoices": return <ErrorBoundary><PortalInvoicesPage /></ErrorBoundary>;
            case "appointments": return <ErrorBoundary><PortalAppointmentsPage /></ErrorBoundary>;
          }
        })()}
      </Suspense>
      </ErrorBoundary>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Top nav */}
      <header className="border-b border-border bg-card/80 backdrop-blur sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center">
              <UsersIcon className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="font-semibold text-sm">Customer Portal</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:inline">
              {customer.first_name} {customer.last_name}
            </span>
            <a href="/" className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
              <ExternalLink className="h-3 w-3" /> Admin
            </a>
            <button onClick={logout} className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1">
              <LogOut className="h-3 w-3" /> Sign Out
            </button>
          </div>
        </div>
        {/* Tabs */}
        <div className="max-w-5xl mx-auto px-4 flex gap-1 pb-0">
          {portalTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setPage(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 text-sm rounded-t-md transition-colors border-b-2",
                  page === tab.id
                    ? "border-primary text-foreground font-medium"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        {renderPortalPage()}
      </main>

      <Toaster position="bottom-left" theme="dark" />
    </div>
  );
}

// ── Admin App ──

function AppShell() {
  const { user, logout, loading } = useAuth();
  const [page, setPage] = useState<PageId>("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (user) {
      api.stats.get().then(setStats).catch(() => {});
      const interval = setInterval(() => {
        api.stats.get().then(setStats).catch(() => {});
      }, 60_000);
      return () => clearInterval(interval);
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
    return (
      <ErrorBoundary>
        <Suspense fallback={<div className="flex items-center justify-center py-20"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>}>
          {(() => {
          switch (page) {
            case "dashboard":
              return <ErrorBoundary><DashboardPage stats={stats} onNavigate={setPage} /></ErrorBoundary>;
            case "customers":
              return <ErrorBoundary><CustomersPage /></ErrorBoundary>;
            case "tickets":
              return <ErrorBoundary><TicketsPage /></ErrorBoundary>;
            case "invoices":
              return <ErrorBoundary><InvoicesPage /></ErrorBoundary>;
            case "recurring-invoices":
              return <ErrorBoundary><RecurringInvoicesPage /></ErrorBoundary>;
            case "payments":
              return <ErrorBoundary><PaymentsPage /></ErrorBoundary>;
            case "payment-methods":
              return <ErrorBoundary><PaymentMethodsPage /></ErrorBoundary>;
            case "pos":
              return <ErrorBoundary><PosPage /></ErrorBoundary>;
            case "appointments":
              return <ErrorBoundary><AppointmentsPage /></ErrorBoundary>;
            case "products":
              return <ErrorBoundary><ProductsPage /></ErrorBoundary>;
            case "estimates":
              return <ErrorBoundary><EstimatesPage /></ErrorBoundary>;
            case "purchase-orders":
              return <ErrorBoundary><PurchaseOrdersPage /></ErrorBoundary>;
            case "import-export":
              return <ErrorBoundary><ImportExportPage /></ErrorBoundary>;
            case "audit-log":
              return <ErrorBoundary><AuditLogPage /></ErrorBoundary>;
            case "health":
              return <ErrorBoundary><HealthPage /></ErrorBoundary>;
            case "custom-fields":
              return <ErrorBoundary><CustomFieldsPage /></ErrorBoundary>;
            case "map":
              return <ErrorBoundary><MapPage /></ErrorBoundary>;
            case "checklist":
              return <ErrorBoundary><ChecklistTemplatesPage /></ErrorBoundary>;
            case "reports":
              return <ErrorBoundary><ReportsPage /></ErrorBoundary>;
            case "settings":
              return <ErrorBoundary><SettingsPage /></ErrorBoundary>;
            case "tenants":
              return <ErrorBoundary><TenantsPage /></ErrorBoundary>;
          }
        })()}
      </Suspense>
      </ErrorBoundary>
    );
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
        {navItems.filter(item => {
          // Role-based nav filtering
          const role = user?.role || "";
          if (role === "admin") return true;
          if (role === "tech") return !["health", "custom-fields", "settings", "import-export", "audit-log"].includes(item.id);
          // front_desk
          return !["health", "custom-fields", "products", "purchase-orders", "reports", "settings", "import-export", "audit-log", "estimates"].includes(item.id);
        }).map((item) => {
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

      {/* Portal link + Logout */}
      <div className="p-2 border-t border-border space-y-1">
        <a
          href="/portal"
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <ExternalLink className="h-4 w-4" />
          <span>Customer Portal</span>
        </a>
        <button
          onClick={toggleTheme}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
        </button>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          <LogOut className="h-4 w-4" />
          <span>Sign out</span>
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

// ── Root ──

export default function App() {
  const pathname = typeof window !== "undefined" ? window.location.pathname : "/";

  // Standalone auth pages
  if (pathname === "/forgot-password") {
    return (
      <QueryProvider>
      <ErrorBoundary>
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>}>
        <ForgotPasswordPage />
      </Suspense>
      </ErrorBoundary>
      </QueryProvider>
    );
  }

  if (pathname === "/reset-password") {
    return (
      <QueryProvider>
      <ErrorBoundary>
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>}>
        <ResetPasswordPage />
      </Suspense>
      </ErrorBoundary>
      </QueryProvider>
    );
  }

  const isPortal = pathname.startsWith("/portal");

  if (isPortal) {
    return (
      <QueryProvider>
      <PortalAuthProvider>
        <PortalShell />
      </PortalAuthProvider>
      </QueryProvider>
    );
  }

  return (
    <QueryProvider>
    <AuthProvider>
      <AppShell />
    </AuthProvider>
    </QueryProvider>
  );
}

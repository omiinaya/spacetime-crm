import { useState, useEffect } from "react";
import {
  Users, Ticket, FileText, CreditCard, Calendar, Package,
} from "lucide-react";
import { api, DashboardStats, ReportsData } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const STATUS_COLORS = ["#22c55e", "#eab308", "#ef4444", "#3b82f6", "#a855f7", "#ec4899", "#6366f1"];

type PageId =
  | "dashboard" | "customers" | "tickets" | "invoices"
  | "payments" | "appointments" | "products" | "estimates"
  | "purchase-orders" | "import-export" | "audit-log" | "pos"
  | "health" | "custom-fields" | "checklist" | "map" | "reports" | "settings" | "tenants"
  | "recurring-invoices" | "payment-methods";

export default function DashboardPage({
  stats,
  onNavigate,
}: {
  stats: DashboardStats | null;
  onNavigate: (p: PageId) => void;
}) {
  const [reports, setReports] = useState<ReportsData | null>(null);

  useEffect(() => {
    api.reports.get().then(setReports).catch(() => {});
  }, []);

  const summaryCards = [
    { label: "Total Customers", value: stats?.total_customers ?? 0, icon: Users, color: "text-blue-400", link: "customers" as PageId },
    { label: "Open Tickets", value: stats?.open_tickets ?? 0, icon: Ticket, color: "text-amber-400", link: "tickets" as PageId },
    { label: "Revenue", value: `$${(stats?.revenue ?? 0).toFixed(2)}`, icon: CreditCard, color: "text-green-400", link: "invoices" as PageId },
    { label: "Upcoming Appointments", value: stats?.upcoming_appointments ?? 0, icon: Calendar, color: "text-purple-400", link: "appointments" as PageId },
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

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Monthly Revenue</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {reports && reports.revenue_by_month.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={reports.revenue_by_month} margin={{ top: 5, right: 5, left: 0, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                  <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" tickFormatter={(v) => `$${v}`} />
                  <Tooltip
                    contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                    formatter={(v: any) => [`$${Number(v).toFixed(2)}`, "Revenue"]}
                  />
                  <Bar dataKey="revenue" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                No revenue data yet
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tickets by Status</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {reports && reports.ticket_by_status.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={reports.ticket_by_status}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={(entry: any) => `${entry.status}: ${entry.count}`}
                  >
                    {reports.ticket_by_status.map((_, i) => (
                      <Cell key={i} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                No ticket data yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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

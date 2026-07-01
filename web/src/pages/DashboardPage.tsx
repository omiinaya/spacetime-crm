import { useState, useEffect } from "react";
import {
  Users, Ticket, FileText, CreditCard, Calendar, Package,
} from "lucide-react";
import { api, DashboardStats, ReportsData } from "../lib/api";
import { Badge } from "../components/ui/badge";
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

      {/* My Tickets section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* My assigned tickets */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Ticket className="w-4 h-4" /> My Tickets
              </CardTitle>
              {stats?.my_ticket_counts && (
                <div className="flex gap-2 text-xs">
                  {stats.my_ticket_counts.urgent > 0 && (
                    <Badge variant="destructive" className="text-xs">{stats.my_ticket_counts.urgent} urgent</Badge>
                  )}
                  {stats.my_ticket_counts.high > 0 && (
                    <Badge className="text-xs bg-orange-500">{stats.my_ticket_counts.high} high</Badge>
                  )}
                  <span className="text-muted-foreground">{stats.my_ticket_counts.all} total</span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {stats?.my_tickets && stats.my_tickets.length > 0 ? (
              <div className="space-y-2">
                {stats.my_tickets.map((ticket) => {
                  const hoursAge = (Date.now() - new Date(ticket.created_at).getTime()) / 3600000;
                  const slaColor = hoursAge < 4 ? "text-green-400" : hoursAge < 24 ? "text-amber-400" : hoursAge < 72 ? "text-red-400" : "text-red-600";
                  return (
                    <div
                      key={ticket.id}
                      className="flex items-center justify-between border rounded-lg p-3 hover:bg-accent cursor-pointer"
                      onClick={() => onNavigate("tickets")}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{ticket.title || "Untitled"}</p>
                        <p className="text-xs text-muted-foreground">
                          <span className={`${slaColor}`}>●</span> {ticket.status === "open" ? "Open" : ticket.status}
                          {ticket.priority && ` · ${ticket.priority}`}
                        </p>
                      </div>
                      <div className="text-right ml-2">
                        <p className="text-sm font-semibold">#{ticket.ticket_number || ticket.id.slice(-6)}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-6">
                No tickets assigned to you
              </p>
            )}
            {stats?.my_tickets && stats.my_tickets.length > 0 && (
              <Button variant="ghost" size="sm" className="w-full mt-2 text-xs" onClick={() => onNavigate("tickets")}>
                View all tickets →
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Today's Appointments + Summary */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Calendar className="w-4 h-4" /> Today's Appointments
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats?.today_appointments && stats.today_appointments.length > 0 ? (
              <div className="space-y-2">
                {stats.today_appointments.slice(0, 5).map((appt) => {
                  const time = new Date(appt.start_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                  return (
                    <div key={appt.id} className="flex items-center justify-between border rounded-lg p-2 hover:bg-accent cursor-pointer" onClick={() => onNavigate("appointments")}>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{appt.title || "Appointment"}</p>
                        <p className="text-xs text-muted-foreground">{time} · {appt.status}</p>
                      </div>
                    </div>
                  );
                })}
                <Button variant="ghost" size="sm" className="w-full mt-1 text-xs" onClick={() => onNavigate("appointments")}>
                  View all →
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-6">
                No appointments today
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

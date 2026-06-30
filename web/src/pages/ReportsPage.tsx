import { useQuery } from "@tanstack/react-query";
import { api, ReportsData } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import { TrendingUp, Ticket, FileText, Calendar, DollarSign, Clock, Users, Award } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  open: "#f59e0b",
  "in progress": "#3b82f6",
  resolved: "#22c55e",
  closed: "#6b7280",
  waiting: "#8b5cf6",
  on_hold: "#ef4444",
};

const INV_STATUS_COLORS: Record<string, string> = {
  draft: "#6b7280",
  sent: "#3b82f6",
  paid: "#22c55e",
  partial: "#f59e0b",
  overdue: "#ef4444",
  cancelled: "#9ca3af",
};

const getStatusColor = (status: string) =>
  STATUS_COLORS[status.toLowerCase()] || "#6b7280";

const getInvStatusColor = (status: string) =>
  INV_STATUS_COLORS[status.toLowerCase()] || "#6b7280";

export default function ReportsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => api.reports.get(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">Failed to load reports.</p>;
  }

  const { revenue_by_month, ticket_by_status, invoice_by_status, appointments_by_month, tech_closed, top_customers, totals } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <TrendingUp className="h-6 w-6" />
          Reports
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Business performance overview
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Total Revenue", value: `$${totals.total_revenue.toFixed(2)}`, icon: DollarSign, color: "text-green-400" },
          { label: "Outstanding", value: `$${totals.outstanding_revenue.toFixed(2)}`, icon: Clock, color: "text-amber-400" },
          { label: "Open Tickets", value: totals.open_tickets, icon: Ticket, color: "text-blue-400" },
          { label: "Avg Resolution", value: totals.avg_resolution_hours ? `${totals.avg_resolution_hours}h` : "N/A", icon: Award, color: "text-purple-400" },
        ].map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label}>
              <CardContent className="pt-4">
                <div className="flex items-center gap-3">
                  <Icon className={`h-5 w-5 ${card.color}`} />
                  <div>
                    <p className="text-xs text-muted-foreground">{card.label}</p>
                    <p className="text-lg font-bold">{card.value}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Revenue by month */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><DollarSign className="h-4 w-4 text-green-400" /> Revenue Trend</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={revenue_by_month}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <Tooltip
                  contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                  formatter={(value: any) => [`$${Number(value || 0).toFixed(2)}`, "Revenue"]}
                />
                <Bar dataKey="revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Ticket by status */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Ticket className="h-4 w-4 text-amber-400" /> Tickets by Status</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={ticket_by_status}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ payload }: any) => `${payload?.status || ''}: ${payload?.count || 0}`}
                  labelLine={true}
                >
                  {ticket_by_status.map((entry) => (
                    <Cell key={entry.status} fill={getStatusColor(entry.status)} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Invoice by status */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><FileText className="h-4 w-4 text-purple-400" /> Invoices by Status</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={invoice_by_status} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <YAxis type="category" dataKey="status" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <Tooltip
                  contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {invoice_by_status.map((entry) => (
                    <Cell key={entry.status} fill={getInvStatusColor(entry.status)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Appointments by month */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Calendar className="h-4 w-4 text-purple-400" /> Appointments by Month</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={appointments_by_month}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                <Tooltip
                  contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                />
                <Line type="monotone" dataKey="appointments" stroke="#8b5cf6" strokeWidth={2} dot={{ fill: "#8b5cf6", r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

      </div>

      {/* Tech Productivity + Top Customers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Tech Productivity */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Users className="h-4 w-4 text-blue-400" /> Tech Productivity — Tickets Closed</CardTitle></CardHeader>
          <CardContent>
            {tech_closed.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">No closed tickets yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(200, tech_closed.length * 50)}>
                <BarChart data={tech_closed} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
                  <YAxis type="category" dataKey="user_name" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" width={120} />
                  <Tooltip
                    contentStyle={{ background: "var(--color-card)", border: "1px solid var(--color-border)", borderRadius: "8px" }}
                  />
                  <Bar dataKey="closed_count" fill="#3b82f6" radius={[0, 4, 4, 0]} name="Closed Tickets" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Top Customers */}
        <Card>
          <CardHeader><CardTitle className="text-sm flex items-center gap-2"><Award className="h-4 w-4 text-amber-400" /> Top Customers by Revenue</CardTitle></CardHeader>
          <CardContent>
            {top_customers.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">No paid invoices yet</p>
            ) : (
              <div className="divide-y divide-border">
                {top_customers.map((c, i) => (
                  <div key={i} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xs font-medium text-muted-foreground w-5 shrink-0">#{i + 1}</span>
                      <span className="text-sm truncate">{c.customer_name}</span>
                    </div>
                    <span className="text-sm font-medium text-green-400 shrink-0">
                      ${c.revenue.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  );
}

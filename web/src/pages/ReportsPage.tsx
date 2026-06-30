import { useQuery } from "@tanstack/react-query";
import { api, ReportsData, ScheduledReport } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import { TrendingUp, Ticket, FileText, Calendar, DollarSign, Clock, Users, Award } from "lucide-react";
import { useState, useEffect, useCallback } from "react";

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

  // Scheduled reports state
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState("revenue");
  const [formFrequency, setFormFrequency] = useState("weekly");
  const [formRecipients, setFormRecipients] = useState("");
  const [schedules, setSchedules] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);

  const loadSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.reportSchedules.list();
      setSchedules(res.schedules || []);
    } catch (e) {
      console.error("Failed to load schedules", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSchedules(); }, [loadSchedules]);

  const handleCreate = async () => {
    if (!formName || !formRecipients) return;
    setCreating(true);
    try {
      await api.reportSchedules.create({
        name: formName,
        report_type: formType,
        schedule_frequency: formFrequency,
        recipients: formRecipients.split(",").map((e: string) => e.trim()).filter(Boolean),
      });
      setFormName("");
      setShowForm(false);
      await loadSchedules();
    } catch (e) {
      console.error("Failed to create schedule", e);
    } finally {
      setCreating(false);
    }
  };

  const handleRunNow = async (id: string) => {
    setRunningId(id);
    try {
      await api.reportSchedules.runNow(id);
      await loadSchedules();
    } catch (e) {
      console.error("Failed to run schedule", e);
    } finally {
      setRunningId(null);
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await api.reportSchedules.update(id, { enabled: !enabled });
      await loadSchedules();
    } catch (e) {
      console.error("Failed to toggle schedule", e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.reportSchedules.delete(id);
      await loadSchedules();
    } catch (e) {
      console.error("Failed to delete schedule", e);
    }
  };

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

      {/* ── Scheduled Reports ── */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-purple-400" />
                Scheduled Reports
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Automatically generate and email reports on a schedule
              </p>
            </div>
            <button
              onClick={() => setShowForm(!showForm)}
              className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity"
            >
              {showForm ? "Cancel" : "+ New Schedule"}
            </button>
          </div>

          {/* Create form */}
          {showForm && (
            <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Name</label>
                  <input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="w-full text-xs px-2 py-1.5 bg-background border border-input rounded-md"
                    placeholder="Weekly Revenue Report"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Report Type</label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full text-xs px-2 py-1.5 bg-background border border-input rounded-md"
                  >
                    <option value="revenue">Revenue</option>
                    <option value="tickets">Tickets</option>
                    <option value="invoices">Invoices</option>
                    <option value="appointments">Appointments</option>
                    <option value="tech_productivity">Tech Productivity</option>
                    <option value="customers">Customers</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Frequency</label>
                  <select
                    value={formFrequency}
                    onChange={(e) => setFormFrequency(e.target.value)}
                    className="w-full text-xs px-2 py-1.5 bg-background border border-input rounded-md"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Recipients (comma-separated)</label>
                  <input
                    value={formRecipients}
                    onChange={(e) => setFormRecipients(e.target.value)}
                    className="w-full text-xs px-2 py-1.5 bg-background border border-input rounded-md"
                    placeholder="admin@example.com, user@example.com"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={handleCreate}
                  disabled={!formName || !formRecipients}
                  className="text-xs px-4 py-1.5 bg-primary text-primary-foreground rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Schedule"}
                </button>
              </div>
            </div>
          )}

          {/* Schedule list */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" />
            </div>
          ) : schedules.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No scheduled reports yet. Create one to get automated email reports.
            </p>
          ) : (
            <div className="divide-y divide-border">
              {schedules.map((s) => {
                const recipients = (() => { try { return JSON.parse(s.recipients_json); } catch { return []; } })();
                const config = (() => { try { return JSON.parse(s.schedule_config_json); } catch { return {}; } })();
                const freqLabel = { daily: "Daily", weekly: "Weekly", monthly: "Monthly" }[s.schedule_frequency] || s.schedule_frequency;
                return (
                  <div key={s.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{s.name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${s.enabled ? "bg-green-500/10 text-green-400" : "bg-muted text-muted-foreground"}`}>
                          {s.enabled ? "Active" : "Paused"}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span className="capitalize">{s.report_type.replace(/_/g, " ")}</span>
                        <span>·</span>
                        <span>{freqLabel}</span>
                        <span>·</span>
                        <span>{recipients.length} recipient(s)</span>
                        {s.last_error && (
                          <>
                            <span>·</span>
                            <span className="text-red-400" title={s.last_error}>⚠ Error</span>
                          </>
                        )}
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        Next: {s.next_run_at > 0 ? new Date(s.next_run_at).toLocaleDateString() : "—"}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => handleRunNow(s.id)}
                        disabled={runningId === s.id}
                        className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md hover:bg-primary/20 disabled:opacity-50"
                      >
                        {runningId === s.id ? "..." : "Run Now"}
                      </button>
                      <button
                        onClick={() => handleToggle(s.id, s.enabled)}
                        className="text-xs px-2 py-1 bg-muted rounded-md hover:bg-muted/80"
                      >
                        {s.enabled ? "Pause" : "Resume"}
                      </button>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="text-xs px-2 py-1 text-red-400 bg-red-500/10 rounded-md hover:bg-red-500/20"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

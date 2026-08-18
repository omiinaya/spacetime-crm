import { useState, useEffect, useCallback } from "react";
import { portalApi, PortalStats, usePortalAuth } from "../lib/portal-auth";
import { formatCurrency } from "../lib/utils";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Ticket, FileText, Calendar, DollarSign, AlertTriangle, RefreshCw } from "lucide-react";

export default function PortalDashboard() {
  const { customer } = usePortalAuth();
  const [stats, setStats] = useState<PortalStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await portalApi.stats.get();
      setStats(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const cards = [
    { label: "Open Tickets", value: stats?.open_tickets ?? "—", icon: Ticket, color: "text-blue-500" },
    { label: "Total Invoices", value: stats?.total_invoices ?? "—", icon: FileText, color: "text-orange-500" },
    { label: "Balance Due", value: stats?.balance_due != null ? formatCurrency(stats.balance_due, "USD") : "—", icon: DollarSign, color: stats?.balance_due ? "text-red-500" : "text-green-500" },
    { label: "Upcoming Appts", value: stats?.upcoming_appointments ?? "—", icon: Calendar, color: "text-purple-500" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome{customer?.first_name ? `, ${customer.first_name}` : ""}!</h1>
      <p className="text-sm text-muted-foreground mt-1">Here's your account at a glance</p>

      {error && (
        <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/10 p-3 mt-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">Failed to load your dashboard. Please try again.</p>
          </div>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry
          </Button>
        </div>
      )}

      {loading && !stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {[0, 1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="animate-pulse space-y-2">
                  <div className="h-8 w-16 rounded bg-muted/60" />
                  <div className="h-3 w-20 rounded bg-muted/40" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <Card key={c.label}>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <Icon className={`h-8 w-8 ${c.color}`} />
                    <div>
                      <p className="text-2xl font-bold">{c.value}</p>
                      <p className="text-xs text-muted-foreground">{c.label}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
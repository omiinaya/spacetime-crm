import { useState, useEffect } from "react";
import { portalApi, PortalStats, usePortalAuth } from "../lib/portal-auth";
import { Card, CardContent } from "../components/ui/card";
import { Ticket, FileText, Calendar, DollarSign } from "lucide-react";

export default function PortalDashboard() {
  const { customer } = usePortalAuth();
  const [stats, setStats] = useState<PortalStats | null>(null);

  useEffect(() => {
    portalApi.stats.get().then(setStats).catch(() => {});
  }, []);

  const cards = [
    { label: "Open Tickets", value: stats?.open_tickets ?? "—", icon: Ticket, color: "text-blue-500" },
    { label: "Total Invoices", value: stats?.total_invoices ?? "—", icon: FileText, color: "text-orange-500" },
    { label: "Balance Due", value: stats?.balance_due != null ? `$${stats.balance_due.toFixed(2)}` : "—", icon: DollarSign, color: stats?.balance_due ? "text-red-500" : "text-green-500" },
    { label: "Upcoming Appts", value: stats?.upcoming_appointments ?? "—", icon: Calendar, color: "text-purple-500" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold">Welcome{customer?.first_name ? `, ${customer.first_name}` : ""}!</h1>
      <p className="text-sm text-muted-foreground mt-1">Here's your account at a glance</p>
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
    </div>
  );
}

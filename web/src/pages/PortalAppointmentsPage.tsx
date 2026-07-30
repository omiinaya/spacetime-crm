import { useState, useEffect } from "react";
import { toast } from "sonner";
import { portalApi, PortalAppointment } from "../lib/portal-auth";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Calendar } from "lucide-react";

const statusColors: Record<
  string,
  "outline" | "default" | "success" | "destructive"
> = {
  scheduled: "default",
  confirmed: "success",
  in_progress: "default",
  completed: "outline",
  cancelled: "destructive",
  no_show: "destructive",
};

export default function PortalAppointmentsPage() {
  const [upcoming, setUpcoming] = useState<PortalAppointment[]>([]);
  const [past, setPast] = useState<PortalAppointment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portalApi.appointments
      .list()
      .then((res) => {
        setUpcoming(res.upcoming);
        setPast(res.past);
      })
      .catch(() => toast.error("Failed to load appointments"))
      .finally(() => setLoading(false));
  }, []);

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };
  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold">My Appointments</h1>
      <p className="text-sm text-muted-foreground mt-1">
        View your scheduled and past appointments
      </p>

      {upcoming.length > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-green-500" /> Upcoming
          </h2>
          <div className="space-y-2">
            {upcoming.map((a) => (
              <Card key={a.id}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={statusColors[a.status] || "outline"}>
                      {a.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="font-medium">{a.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(a.start_time)} at {formatTime(a.start_time)}
                    {a.end_time ? ` — ${formatTime(a.end_time)}` : ""}
                  </p>
                  {a.description && (
                    <p className="text-sm mt-1">{a.description}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-3 text-muted-foreground">
            Past Appointments
          </h2>
          <div className="space-y-2">
            {past.map((a) => (
              <Card key={a.id}>
                <CardContent className="pt-4 opacity-70">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={statusColors[a.status] || "outline"}>
                      {a.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <p className="font-medium">{a.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(a.start_time)} at {formatTime(a.start_time)}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {!loading && upcoming.length === 0 && past.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">
          No appointments found
        </p>
      )}
    </div>
  );
}

import { useState, useEffect } from "react";
import { api, Appointment, Customer } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Calendar, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, "default" | "secondary" | "warning" | "success" | "destructive" | "outline"> = {
  scheduled: "outline",
  confirmed: "default",
  checked_in: "warning",
  started: "default",
  completed: "success",
  cancelled: "destructive",
};

export default function AppointmentsPage() {
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", ticket_id: "", title: "", description: "", start_time: "", end_time: "", all_day: false });

  const load = async () => {
    try {
      const [aRes, cRes] = await Promise.all([api.appointments.list(), api.customers.list()]);
      setAppts(aRes.appointments);
      setCustomers(cRes.customers);
    } catch { toast.error("Failed to load appointments"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    try {
      await api.appointments.create({
        ...form,
        start_time: form.start_time ? new Date(form.start_time).getTime() : 0,
        end_time: form.end_time ? new Date(form.end_time).getTime() : 0,
      });
      toast.success("Appointment created");
      setShowForm(false);
      setForm({ customer_id: "", ticket_id: "", title: "", description: "", start_time: "", end_time: "", all_day: false });
      load();
    } catch { toast.error("Failed to create appointment"); }
  };

  const handleStatus = async (id: string, status: string) => {
    await api.appointments.updateStatus(id, status);
    load();
  };

  const handleDelete = async (id: string) => {
    await api.appointments.delete(id);
    toast.success("Appointment deleted");
    load();
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Appointments</h1>
          <p className="text-sm text-muted-foreground mt-1">Schedule and manage appointments</p>
        </div>
        <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-1.5" />New Appointment</Button>
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>New Appointment</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (<option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>))}
            </Select>
            <Input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input type="datetime-local" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
              <Input type="datetime-local" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
            </div>
            <Input placeholder="Ticket ID (optional)" value={form.ticket_id} onChange={(e) => setForm({ ...form, ticket_id: e.target.value })} />
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {appts.map((a) => {
          const cust = customers.find((c) => c.id === a.customer_id);
          return (
            <Card key={a.id}>
              <CardContent className="pt-4 flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={statusColors[a.status] || "outline"}>{a.status}</Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(a.start_time / 1000).toLocaleString()}
                    </span>
                  </div>
                  <p className="font-medium mt-1 truncate">{a.title}</p>
                  {cust && <p className="text-xs text-muted-foreground">{cust.first_name} {cust.last_name}</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <Select value={a.status} onChange={(e) => handleStatus(a.id, e.target.value)} className="w-32">
                    <option value="scheduled">Scheduled</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="checked_in">Checked In</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </Select>
                  <Button size="icon" variant="ghost" onClick={() => handleDelete(a.id)}><Trash2 className="h-3.5 w-3.5 text-destructive" /></Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}

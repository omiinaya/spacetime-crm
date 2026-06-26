import { useState, useEffect } from "react";
import { api, Ticket, Customer } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Ticket as TicketIcon, Plus, MessageSquare } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, "default" | "secondary" | "warning" | "success" | "outline"> = {
  new: "default",
  assigned: "secondary",
  in_progress: "warning",
  waiting_on_customer: "outline",
  resolved: "success",
  closed: "secondary",
};

const priorityColors: Record<string, string> = {
  low: "text-slate-400",
  medium: "text-amber-400",
  high: "text-orange-400",
  urgent: "text-destructive",
};

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", title: "", description: "", device_type: "", device_model: "", device_serial: "", priority: "medium" });
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [newNote, setNewNote] = useState("");

  const load = async () => {
    try {
      const [tRes, cRes] = await Promise.all([
        api.tickets.list(filter),
        api.customers.list(),
      ]);
      setTickets(tRes.tickets);
      setCustomers(cRes.customers);
    } catch {
      toast.error("Failed to load tickets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleCreate = async () => {
    try {
      await api.tickets.create(form);
      toast.success("Ticket created");
      setShowForm(false);
      setForm({ customer_id: "", title: "", description: "", device_type: "", device_model: "", device_serial: "", priority: "medium" });
      load();
    } catch {
      toast.error("Failed to create ticket");
    }
  };

  const handleStatusChange = async (id: string, status: string) => {
    await api.tickets.updateStatus(id, status);
    load();
  };

  const viewTicket = async (t: Ticket) => {
    setSelectedTicket(t);
    try {
      const res = await api.tickets.notes.list(t.id);
      setNotes(res.notes);
      setNewNote("");
    } catch { setNotes([]); }
  };

  const addNote = async () => {
    if (!newNote.trim() || !selectedTicket) return;
    try {
      await api.tickets.notes.create(selectedTicket.id, { author: "User", content: newNote, internal: false });
      const res = await api.tickets.notes.list(selectedTicket.id);
      setNotes(res.notes);
      setNewNote("");
    } catch {
      toast.error("Failed to add note");
    }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tickets</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage repair tickets</p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1.5" /> New Ticket
        </Button>
      </div>

      <div className="flex gap-2">
        {["", "new", "assigned", "in_progress", "waiting_on_customer", "resolved", "closed"].map((s) => (
          <Button key={s} size="sm" variant={filter === s ? "default" : "outline"} onClick={() => setFilter(s)}>
            {s || "All"}
          </Button>
        ))}
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader><CardTitle>New Ticket</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
              ))}
            </Select>
            <Input placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="grid grid-cols-3 gap-2">
              <Input placeholder="Device type" value={form.device_type} onChange={(e) => setForm({ ...form, device_type: e.target.value })} />
              <Input placeholder="Device model" value={form.device_model} onChange={(e) => setForm({ ...form, device_model: e.target.value })} />
              <Input placeholder="Serial" value={form.device_serial} onChange={(e) => setForm({ ...form, device_serial: e.target.value })} />
            </div>
            <Select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </Select>
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ticket list & detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          {tickets.map((t) => {
            const cust = customers.find((c) => c.id === t.customer_id);
            return (
              <Card key={t.id} className={`cursor-pointer transition-colors ${selectedTicket?.id === t.id ? "border-primary" : "hover:border-primary/30"}`} onClick={() => viewTicket(t)}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">#{t.ticket_number}</span>
                        <Badge variant={statusColors[t.status] || "secondary"}>{t.status}</Badge>
                        <span className={`text-xs ${priorityColors[t.priority] || ""}`}>{t.priority}</span>
                      </div>
                      <p className="font-medium mt-1 truncate">{t.title}</p>
                      {cust && <p className="text-xs text-muted-foreground">{cust.first_name} {cust.last_name}</p>}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Detail panel */}
        {selectedTicket && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>#{selectedTicket.ticket_number} — {selectedTicket.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">{selectedTicket.description || "No description"}</p>
                {selectedTicket.device_type && (
                  <p className="text-xs text-muted-foreground">Device: {selectedTicket.device_type} {selectedTicket.device_model} ({selectedTicket.device_serial})</p>
                )}
                <Select value={selectedTicket.status} onChange={(e) => handleStatusChange(selectedTicket.id, e.target.value)}>
                  <option value="new">New</option>
                  <option value="assigned">Assigned</option>
                  <option value="in_progress">In Progress</option>
                  <option value="waiting_on_customer">Waiting on Customer</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </Select>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader><CardTitle><MessageSquare className="h-4 w-4 inline mr-1.5" />Notes</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {notes.map((n) => (
                    <div key={n.id} className="text-sm p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">{n.author} — {new Date(n.created_at / 1000).toLocaleString()}</p>
                      <p className="mt-1">{n.content}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="Add note..." value={newNote} onChange={(e) => setNewNote(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addNote()} />
                  <Button size="sm" onClick={addNote}>Send</Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </>
  );
}

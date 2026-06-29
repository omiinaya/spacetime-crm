import { useState, useEffect } from "react";
import { api, Ticket, Customer, TicketTimer, ChecklistTemplate, TicketChecklistItem } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Ticket as TicketIcon, Plus, MessageSquare, Timer, StopCircle, Play, ListChecks } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";
import { usePagination } from "../lib/usePagination";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 25;

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
  const pag = usePagination(PAGE_SIZE);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", title: "", description: "", device_type: "", device_model: "", device_serial: "", priority: "medium" });
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [notes, setNotes] = useState<any[]>([]);
  const [newNote, setNewNote] = useState("");
  const [timers, setTimers] = useState<TicketTimer[]>([]);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [checklist, setChecklist] = useState<TicketChecklistItem[]>([]);
  const [checklistTemplates, setChecklistTemplates] = useState<ChecklistTemplate[]>([]);
  const [showApplyTemplate, setShowApplyTemplate] = useState(false);
  const { user } = useAuth();

  const load = async (offset: number) => {
    try {
      const [tRes, cRes] = await Promise.all([
        api.tickets.list(filter, offset, PAGE_SIZE),
        api.customers.list(),
      ]);
      setTickets(tRes.tickets);
      setCustomers(cRes.customers);
      pag.setTotal(tRes.total);
    } catch {
      toast.error("Failed to load tickets");
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = (val: string) => {
    setFilter(val);
    pag.reset();
  };

  useEffect(() => { load(pag.offset); }, [filter, pag.offset]);

  const loadTimers = async (ticketId: string) => {
    try {
      const res = await api.tickets.timers.list(ticketId);
      setTimers(res.timers);
      const running = res.timers.find((t) => t.running);
      if (running) {
        setTimerSeconds(running.total_seconds + Math.floor((Date.now() - running.start_time) / 1000));
      } else {
        setTimerSeconds(0);
      }
    } catch { setTimers([]); }
  };

  // Tick every second for running timer display
  useEffect(() => {
    if (!timers.some((t) => t.running)) return;
    const interval = setInterval(() => {
      setTimerSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [timers]);

  const handleStartTimer = async () => {
    if (!selectedTicket || !user) return;
    try {
      await api.tickets.timers.start(selectedTicket.id, user.id);
      await loadTimers(selectedTicket.id);
      toast.success("Timer started");
    } catch { toast.error("Failed to start timer"); }
  };

  const handleStopTimer = async () => {
    const running = timers.find((t) => t.running);
    if (!running) return;
    try {
      await api.tickets.timers.stop(running.id);
      await loadTimers(selectedTicket!.id);
      toast.success("Timer stopped");
    } catch { toast.error("Failed to stop timer"); }
  };

  const fmtTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const totalTrackedTime = () => {
    return timers.reduce((sum, t) => {
      if (t.running) return sum + timerSeconds;
      return sum + t.total_seconds;
    }, 0);
  };

  const handleCreate = async () => {
    try {
      await api.tickets.create(form);
      toast.success("Ticket created");
      setShowForm(false);
      setForm({ customer_id: "", title: "", description: "", device_type: "", device_model: "", device_serial: "", priority: "medium" });
      load(pag.offset);
    } catch {
      toast.error("Failed to create ticket");
    }
  };

  const handleStatusChange = async (id: string, status: string) => {
    await api.tickets.updateStatus(id, status);
    load(pag.offset);
  };

  const viewTicket = async (t: Ticket) => {
    setSelectedTicket(t);
    try {
      const [noteRes] = await Promise.all([
        api.tickets.notes.list(t.id),
        loadTimers(t.id),
      ]);
      setNotes(noteRes.notes);
      setNewNote("");
    } catch { setNotes([]); }
    loadChecklist(t.id);
    loadTemplates();
  };

  const loadChecklist = async (ticketId: string) => {
    try {
      const res = await api.checklist.ticket.list(ticketId);
      setChecklist(res.items);
    } catch { setChecklist([]); }
  };

  const loadTemplates = async () => {
    try {
      const res = await api.checklist.templates.list();
      setChecklistTemplates(res.templates);
    } catch { setChecklistTemplates([]); }
  };

  const handleApplyTemplate = async (templateId: string) => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.apply(selectedTicket.id, templateId);
      toast.success("Checklist applied");
      setShowApplyTemplate(false);
      loadChecklist(selectedTicket.id);
    } catch { toast.error("Failed to apply checklist"); }
  };

  const handleToggleChecklist = async (item: TicketChecklistItem) => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.toggle(selectedTicket.id, item.id, !item.completed);
      loadChecklist(selectedTicket.id);
    } catch { toast.error("Failed to update checklist item"); }
  };

  const handleClearChecklist = async () => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.clear(selectedTicket.id);
      toast.success("Checklist cleared");
      setChecklist([]);
    } catch { toast.error("Failed to clear checklist"); }
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
          <Button key={s} size="sm" variant={filter === s ? "default" : "outline"} onClick={() => handleFilter(s)}>
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

            {/* Timer */}
            <Card>
              <CardHeader>
                <CardTitle><Timer className="h-4 w-4 inline mr-1.5" />Time Tracking</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-2xl font-mono font-bold">{fmtTime(totalTrackedTime())}</span>
                    <p className="text-xs text-muted-foreground mt-1">Total time logged</p>
                  </div>
                  <div className="flex gap-2">
                    {timers.some((t) => t.running) ? (
                      <Button size="sm" variant="destructive" onClick={handleStopTimer}>
                        <StopCircle className="h-4 w-4 mr-1" /> Stop
                      </Button>
                    ) : (
                      <Button size="sm" variant="default" onClick={handleStartTimer}>
                        <Play className="h-4 w-4 mr-1" /> Start Timer
                      </Button>
                    )}
                  </div>
                </div>
                {timers.length > 0 && (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {timers.slice().reverse().map((tmr) => (
                      <div key={tmr.id} className="flex items-center justify-between text-xs p-2 rounded bg-muted/50">
                        <span className="text-muted-foreground">
                          {new Date(tmr.start_time).toLocaleString()}
                        </span>
                        <span className="font-mono">
                          {tmr.running ? fmtTime(timerSeconds) : fmtTime(tmr.total_seconds)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Checklist */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle><ListChecks className="h-4 w-4 inline mr-1.5" />Checklist</CardTitle>
                  <div className="flex gap-1">
                    {checklist.some(i => i.template_id) && (
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleClearChecklist}>
                        Clear
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setShowApplyTemplate(!showApplyTemplate)}>
                      Apply Template
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {showApplyTemplate && (
                  <div className="mb-3 p-2 rounded bg-muted/50 space-y-1">
                    <p className="text-xs font-medium text-muted-foreground mb-1">Choose a template:</p>
                    {checklistTemplates.length === 0 ? (
                      <p className="text-xs text-muted-foreground">No templates available. Create one in Settings.</p>
                    ) : (
                      checklistTemplates.map(t => (
                        <Button key={t.id} variant="outline" size="sm" className="w-full justify-start text-xs h-7" onClick={() => handleApplyTemplate(t.id)}>
                          <ListChecks className="h-3 w-3 mr-1.5" />
                          {t.name}
                        </Button>
                      ))
                    )}
                  </div>
                )}
                {checklist.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">No checklist items</p>
                ) : (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {checklist.map(item => (
                      <div
                        key={item.id}
                        className={`flex items-center gap-3 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors hover:bg-muted/50 ${item.completed ? "text-muted-foreground line-through" : ""}`}
                        onClick={() => handleToggleChecklist(item)}
                      >
                        <div className={`w-4 h-4 rounded border-2 shrink-0 flex items-center justify-center transition-colors ${item.completed ? "bg-primary border-primary" : "border-muted-foreground/40"}`}>
                          {item.completed && <div className="w-2 h-2 rounded-sm bg-white" />}
                        </div>
                        <span className="flex-1">{item.label}</span>
                        {item.template_name && (
                          <span className="text-[10px] text-muted-foreground shrink-0">{item.template_name}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  {checklist.filter(i => i.completed).length}/{checklist.length} completed
                </p>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader><CardTitle><MessageSquare className="h-4 w-4 inline mr-1.5" />Notes</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {notes.map((n) => (
                    <div key={n.id} className="text-sm p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">{n.author} — {new Date(n.created_at).toLocaleString()}</p>
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

      <Pagination
        page={pag.page}
        totalPages={pag.totalPages}
        total={pag.total}
        hasPrev={pag.hasPrev}
        hasNext={pag.hasNext}
        onPrev={pag.prevPage}
        onNext={pag.nextPage}
        onGoToPage={pag.goToPage}
      />
    </>
  );
}

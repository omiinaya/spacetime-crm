import { useState, useEffect } from "react";
import { api, Appointment, Customer } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import MonthCalendar from "../components/MonthCalendar";
import { Plus, Trash2, ChevronLeft, ChevronRight, Calendar, Clock } from "lucide-react";

const PAGE_SIZE = 25;

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
  const pag = usePagination(PAGE_SIZE);
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ customer_id: "", ticket_id: "", title: "", description: "", start_time: "", end_time: "", all_day: false });

  // Calendar state
  const now = new Date();
  const [calYear, setCalYear] = useState(now.getFullYear());
  const [calMonth, setCalMonth] = useState(now.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(now.getDate());

  const load = async (offset: number) => {
    try {
      const [aRes, cRes] = await Promise.all([api.appointments.list(offset, PAGE_SIZE), api.customers.list()]);
      setAppts(aRes.appointments);
      setCustomers(cRes.customers);
      pag.setTotal(aRes.total);
    } catch { toast.error("Failed to load appointments"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(pag.offset); }, [pag.offset]);

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
      load(pag.offset);
    } catch { toast.error("Failed to create appointment"); }
  };

  const handleStatus = async (id: string, status: string) => {
    await api.appointments.updateStatus(id, status);
    load(pag.offset);
  };

  const handleDelete = async (id: string) => {
    await api.appointments.delete(id);
    toast.success("Appointment deleted");
    load(pag.offset);
  };

  const setFormDate = (day: number) => {
    const d = new Date(calYear, calMonth, day);
    const yyyymmdd = d.toISOString().slice(0, 10);
    setForm({
      ...form,
      start_time: `${yyyymmdd}T09:00`,
      end_time: `${yyyymmdd}T10:00`,
    });
    setShowForm(true);
  };

  // Appointments for selected day
  const dayAppts = appts.filter((a) => {
    if (!a.start_time || selectedDay === null) return false;
    const d = new Date(a.start_time);
    return d.getFullYear() === calYear && d.getMonth() === calMonth && d.getDate() === selectedDay;
  }).sort((a, b) => a.start_time - b.start_time);

  const customerName = (id: string) => {
    const c = customers.find((c) => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : "—";
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Appointments</h1>
          <p className="text-sm text-muted-foreground mt-1">Schedule and manage appointments</p>
        </div>
        <Button onClick={() => { setForm({ ...form, start_time: "", end_time: "" }); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1.5" />New Appointment
        </Button>
      </div>

      {/* Calendar + Day detail split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Calendar */}
        <Card>
          <CardContent className="pt-4">
            <MonthCalendar
              year={calYear}
              month={calMonth}
              events={appts}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
              onPrevMonth={() => {
                if (calMonth === 0) { setCalYear(calYear - 1); setCalMonth(11); }
                else { setCalMonth(calMonth - 1); }
                setSelectedDay(null);
              }}
              onNextMonth={() => {
                if (calMonth === 11) { setCalYear(calYear + 1); setCalMonth(0); }
                else { setCalMonth(calMonth + 1); }
                setSelectedDay(null);
              }}
            />
          </CardContent>
        </Card>

        {/* Day detail panel */}
        <div className="space-y-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-sm">
                {selectedDay
                  ? new Date(calYear, calMonth, selectedDay).toLocaleDateString("en-US", {
                      weekday: "long", month: "long", day: "numeric", year: "numeric",
                    })
                  : "Select a day"}
              </CardTitle>
              {selectedDay && (
                <Button size="sm" variant="outline" onClick={() => setFormDate(selectedDay)}>
                  <Plus className="h-3.5 w-3.5 mr-1" />Add
                </Button>
              )}
            </CardHeader>
          </Card>

          {dayAppts.length === 0 && selectedDay !== null && (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No appointments this day</p>
              <Button size="sm" variant="outline" className="mt-2" onClick={() => setFormDate(selectedDay!)}>
                <Plus className="h-3.5 w-3.5 mr-1" />Add appointment
              </Button>
            </div>
          )}

          {dayAppts.map((a) => {
            const startStr = new Date(a.start_time).toLocaleTimeString("en-US", {
              hour: "numeric", minute: "2-digit",
            });
            return (
              <Card key={a.id}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={statusColors[a.status] || "outline"}>{a.status}</Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {startStr}
                        </span>
                      </div>
                      <p className="font-medium mt-1">{a.title}</p>
                      <p className="text-xs text-muted-foreground">{customerName(a.customer_id)}</p>
                      {a.description && (
                        <p className="text-xs text-muted-foreground/70 mt-1">{a.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <Select
                        value={a.status}
                        onChange={(e) => handleStatus(a.id, e.target.value)}
                        className="w-28"
                      >
                        <option value="scheduled">Scheduled</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="checked_in">Checked In</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                      </Select>
                      <Button size="icon" variant="ghost" onClick={() => handleDelete(a.id)}>
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Create form modal */}
      {showForm && (
        <Card className="border-primary/30 mt-4">
          <CardHeader>
            <CardTitle>New Appointment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })}>
              <option value="">Select customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>
              ))}
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

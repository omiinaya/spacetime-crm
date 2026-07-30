import { useState, useEffect } from "react";
import { useQuery, useMutation, keepPreviousData } from "@tanstack/react-query";
import { queryClient } from "../lib/query-client";
import { api, Appointment, Customer } from "../lib/api";
import { usePagination } from "../lib/usePagination";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import Pagination from "../components/Pagination";
import MonthCalendar from "../components/MonthCalendar";
import { Plus, Trash2, Calendar, Clock, Repeat, Play } from "lucide-react";

const PAGE_SIZE = 25;

import { toast } from "sonner";

const statusColors: Record<
  string,
  "default" | "secondary" | "warning" | "success" | "destructive" | "outline"
> = {
  scheduled: "outline",
  confirmed: "default",
  checked_in: "warning",
  started: "default",
  completed: "success",
  cancelled: "destructive",
};

const RECURRENCE_LABELS: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  biweekly: "Biweekly",
  monthly: "Monthly",
};

export default function AppointmentsPage() {
  const pag = usePagination(PAGE_SIZE);
  const [showForm, setShowForm] = useState(false);
  const [showRecurringPanel, setShowRecurringPanel] = useState(false);
  const [form, setForm] = useState({
    customer_id: "",
    ticket_id: "",
    title: "",
    description: "",
    start_time: "",
    end_time: "",
    all_day: false,
    series_id: "",
    recurrence_rule: "",
  });

  // Calendar state
  const now = new Date();
  const [calYear, setCalYear] = useState(now.getFullYear());
  const [calMonth, setCalMonth] = useState(now.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(now.getDate());

  // ── React Query: appointments list ──
  const { data: apptsData, isLoading } = useQuery({
    queryKey: ["appointments", { offset: pag.offset }],
    queryFn: () => api.appointments.list(pag.offset, PAGE_SIZE),
    placeholderData: keepPreviousData,
  });

  // Sync pagination total from query data
  useEffect(() => {
    if (apptsData?.total !== undefined) {
      pag.setTotal(apptsData.total);
    }
  }, [apptsData?.total]);

  // ── React Query: customers for dropdown ──
  const { data: customersData } = useQuery({
    queryKey: ["customers"],
    queryFn: () => api.customers.list(),
    staleTime: 60_000,
  });

  // ── React Query: recurring series ──
  const { data: recurringData } = useQuery({
    queryKey: ["appointments", "recurring"],
    queryFn: () => api.appointments.recurring.list(),
    staleTime: 30_000,
  });

  const appts = apptsData?.appointments ?? [];
  const customers = customersData?.customers ?? [];
  const recurringSeries = recurringData?.series ?? [];

  // ── Mutations ──
  const createMutation = useMutation({
    mutationFn: () =>
      api.appointments.create({
        ...form,
        start_time: form.start_time ? new Date(form.start_time).getTime() : 0,
        end_time: form.end_time ? new Date(form.end_time).getTime() : 0,
      }),
    onSuccess: () => {
      toast.success("Appointment created");
      setShowForm(false);
      setForm({
        customer_id: "",
        ticket_id: "",
        title: "",
        description: "",
        start_time: "",
        end_time: "",
        all_day: false,
        series_id: "",
        recurrence_rule: "",
      });
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({
        queryKey: ["appointments", "recurring"],
      });
    },
    onError: () => {
      toast.error("Failed to create appointment");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.appointments.updateStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.appointments.delete(id),
    onSuccess: () => {
      toast.success("Appointment deleted");
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({
        queryKey: ["appointments", "recurring"],
      });
    },
    onError: () => {
      toast.error("Failed to delete appointment");
    },
  });

  const generateNextMutation = useMutation({
    mutationFn: (seriesId: string) => api.appointments.generateNext(seriesId),
    onSuccess: (res) => {
      if (res.ok) {
        toast.success("Next occurrence created");
        queryClient.invalidateQueries({ queryKey: ["appointments"] });
        queryClient.invalidateQueries({
          queryKey: ["appointments", "recurring"],
        });
      } else {
        toast.error(res.error || "Failed to generate next");
      }
    },
    onError: () => toast.error("Failed to generate next occurrence"),
  });

  const handleCreate = () => createMutation.mutate();
  const handleStatus = (id: string, status: string) =>
    statusMutation.mutate({ id, status });
  const handleDelete = (id: string) => deleteMutation.mutate(id);

  // ── Derived data ──
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
  const dayAppts = appts
    .filter((a) => {
      if (!a.start_time || selectedDay === null) return false;
      const d = new Date(a.start_time);
      return (
        d.getFullYear() === calYear &&
        d.getMonth() === calMonth &&
        d.getDate() === selectedDay
      );
    })
    .sort((a, b) => a.start_time - b.start_time);

  const customerName = (id: string) => {
    const c = customers.find((c) => c.id === id);
    return c ? `${c.first_name} ${c.last_name}` : "—";
  };

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">Appointments</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Schedule and manage appointments
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowRecurringPanel(!showRecurringPanel)}
          >
            <Repeat className="h-4 w-4 mr-1.5" />
            Recurring
          </Button>
          <Button
            onClick={() => {
              setForm({
                ...form,
                start_time: "",
                end_time: "",
                recurrence_rule: "",
              });
              setShowForm(true);
            }}
          >
            <Plus className="h-4 w-4 mr-1.5" />
            New Appointment
          </Button>
        </div>
      </div>

      {/* Recurring series panel */}
      {showRecurringPanel && (
        <Card className="border-indigo-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Repeat className="h-4 w-4" /> Recurring Series
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recurringSeries.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No recurring appointment series yet. Set a recurrence rule when
                creating an appointment.
              </p>
            )}
            <div className="space-y-2">
              {recurringSeries.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Repeat className="h-4 w-4 text-indigo-400 shrink-0" />
                      <span className="font-medium">{s.title}</span>
                      <Badge variant="outline" className="text-[10px]">
                        {RECURRENCE_LABELS[s.recurrence_rule] ||
                          s.recurrence_rule}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {customerName(s.customer_id)}
                      {(s as any).occurrence_count > 0 && (
                        <span>
                          {" "}
                          &middot; {(s as any).occurrence_count} occurrence
                          {(s as any).occurrence_count !== 1 ? "s" : ""}
                        </span>
                      )}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => generateNextMutation.mutate(s.id)}
                    disabled={generateNextMutation.isPending}
                  >
                    <Play className="h-3.5 w-3.5 mr-1" /> Generate Next
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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
                if (calMonth === 0) {
                  setCalYear(calYear - 1);
                  setCalMonth(11);
                } else {
                  setCalMonth(calMonth - 1);
                }
                setSelectedDay(null);
              }}
              onNextMonth={() => {
                if (calMonth === 11) {
                  setCalYear(calYear + 1);
                  setCalMonth(0);
                } else {
                  setCalMonth(calMonth + 1);
                }
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
                  ? new Date(calYear, calMonth, selectedDay).toLocaleDateString(
                      "en-US",
                      {
                        weekday: "long",
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      },
                    )
                  : "Select a day"}
              </CardTitle>
              {selectedDay && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setFormDate(selectedDay)}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add
                </Button>
              )}
            </CardHeader>
          </Card>

          {dayAppts.length === 0 && selectedDay !== null && (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="h-10 w-10 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No appointments this day</p>
              <Button
                size="sm"
                variant="outline"
                className="mt-2"
                onClick={() => setFormDate(selectedDay!)}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Add appointment
              </Button>
            </div>
          )}

          {dayAppts.map((a) => {
            const startStr = new Date(a.start_time).toLocaleTimeString(
              "en-US",
              {
                hour: "numeric",
                minute: "2-digit",
              },
            );
            const isRecurring = a.recurrence_rule !== "" && a.series_id === "";
            return (
              <Card key={a.id}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={statusColors[a.status] || "outline"}>
                          {a.status}
                        </Badge>
                        {isRecurring && (
                          <Badge
                            variant="outline"
                            className="text-[10px] border-indigo-500/40 text-indigo-400"
                          >
                            <Repeat className="h-3 w-3 mr-0.5 inline" />
                            {RECURRENCE_LABELS[a.recurrence_rule] ||
                              a.recurrence_rule}
                          </Badge>
                        )}
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> {startStr}
                        </span>
                      </div>
                      <p className="font-medium mt-1">{a.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {customerName(a.customer_id)}
                      </p>
                      {a.description && (
                        <p className="text-xs text-muted-foreground/70 mt-1">
                          {a.description}
                        </p>
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
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleDelete(a.id)}
                      >
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
            <Select
              value={form.customer_id}
              onChange={(e) =>
                setForm({ ...form, customer_id: e.target.value })
              }
            >
              <option value="">Select customer...</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.first_name} {c.last_name}
                </option>
              ))}
            </Select>
            <Input
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <Input
              placeholder="Description"
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
            <div className="grid grid-cols-2 gap-2">
              <Input
                type="datetime-local"
                value={form.start_time}
                onChange={(e) =>
                  setForm({ ...form, start_time: e.target.value })
                }
              />
              <Input
                type="datetime-local"
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              />
            </div>
            <Input
              placeholder="Ticket ID (optional)"
              value={form.ticket_id}
              onChange={(e) => setForm({ ...form, ticket_id: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <Select
                value={form.recurrence_rule}
                onChange={(e) =>
                  setForm({ ...form, recurrence_rule: e.target.value })
                }
              >
                <option value="">No repeat</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Biweekly</option>
                <option value="monthly">Monthly</option>
              </Select>
            </div>
            {form.recurrence_rule && (
              <p className="text-xs text-indigo-400">
                <Repeat className="h-3 w-3 inline mr-1" />
                This will create a recurring series. Use "Generate Next" to
                create future occurrences.
              </p>
            )}
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
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

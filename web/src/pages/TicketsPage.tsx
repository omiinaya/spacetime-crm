import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../lib/query-client';
import {
  api,
  Ticket,
  Customer,
  TicketTimer,
  ChecklistTemplate,
  TicketChecklistItem,
} from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import {
  Ticket as TicketIcon,
  Plus,
  MessageSquare,
  Timer,
  StopCircle,
  Play,
  ListChecks,
  AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../lib/auth';
import { usePagination } from '../lib/usePagination';
import Pagination from '../components/Pagination';

const PAGE_SIZE = 25;

const statusColors: Record<string, 'default' | 'secondary' | 'warning' | 'success' | 'outline'> = {
  new: 'default',
  assigned: 'secondary',
  in_progress: 'warning',
  waiting_on_customer: 'outline',
  resolved: 'success',
  closed: 'secondary',
};

const priorityColors: Record<string, string> = {
  low: 'text-blue-400',
  medium: 'text-yellow-400',
  high: 'text-orange-400',
  urgent: 'text-red-400',
};

const slaUrgency = (createdAt: number): { color: string; label: string } => {
  const hours = (Date.now() - createdAt) / 3600000;
  if (hours < 4) return { color: 'bg-green-500', label: `${Math.round(hours)}h` };
  if (hours < 24) return { color: 'bg-amber-500', label: `${Math.round(hours)}h` };
  if (hours < 72) return { color: 'bg-red-500', label: `${Math.floor(hours / 24)}d` };
  return { color: 'bg-red-700', label: `${Math.floor(hours / 24)}d` };
};

export default function TicketsPage() {
  const pag = usePagination(PAGE_SIZE);
  const [filter, setFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    customer_id: '',
    title: '',
    description: '',
    device_type: '',
    device_model: '',
    device_serial: '',
    device_imei: '',
    device_password: '',
    priority: 'medium',
  });
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [newNote, setNewNote] = useState('');
  const [timers, setTimers] = useState<TicketTimer[]>([]);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [checklist, setChecklist] = useState<TicketChecklistItem[]>([]);
  const [checklistTemplates, setChecklistTemplates] = useState<ChecklistTemplate[]>([]);
  const [showApplyTemplate, setShowApplyTemplate] = useState(false);
  const { user } = useAuth();

  const { data, isLoading } = useQuery({
    queryKey: ['tickets', { filter, offset: pag.offset }],
    queryFn: async () => {
      const [tRes, cRes] = await Promise.all([
        api.tickets.list(filter, undefined, pag.offset, PAGE_SIZE),
        api.customers.list(),
      ]);
      return {
        tickets: tRes.tickets,
        customers: cRes.customers,
        total: tRes.total,
      };
    },
    select: (res) => {
      pag.setTotal(res.total);
      return { tickets: res.tickets, customers: res.customers };
    },
  });

  const tickets = data?.tickets ?? [];
  const customers = data?.customers ?? [];

  // SLA breaches — auto-refresh
  const { data: breachData } = useQuery({
    queryKey: ['tickets', 'sla-breaches'],
    queryFn: () => api.tickets.sla.breaches(),
    refetchInterval: 60_000,
  });
  const breachCount = breachData?.count ?? 0;
  const breachedIds = new Set(breachData?.breaches?.map((b) => b.id) ?? []);

  // Notes query — only active when a ticket is selected
  const { data: notesData } = useQuery({
    queryKey: ['ticket-notes', selectedTicket?.id],
    queryFn: async () => {
      const res = await api.tickets.notes.list(selectedTicket!.id);
      return res.notes;
    },
    enabled: !!selectedTicket,
  });
  const notes = notesData ?? [];

  const handleFilter = (val: string) => {
    setFilter(val);
    pag.reset();
  };

  const loadTimers = async (ticketId: string) => {
    try {
      const res = await api.tickets.timers.list(ticketId);
      setTimers(res.timers);
      const running = res.timers.find((t) => t.running);
      if (running) {
        setTimerSeconds(
          running.total_seconds + Math.floor((Date.now() - running.start_time) / 1000),
        );
      } else {
        setTimerSeconds(0);
      }
    } catch {
      setTimers([]);
    }
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
      toast.success('Timer started');
    } catch {
      toast.error('Failed to start timer');
    }
  };

  const handleStopTimer = async () => {
    const running = timers.find((t) => t.running);
    if (!running) return;
    try {
      await api.tickets.timers.stop(running.id);
      await loadTimers(selectedTicket!.id);
      toast.success('Timer stopped');
    } catch {
      toast.error('Failed to stop timer');
    }
  };

  const fmtTime = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const totalTrackedTime = () => {
    return timers.reduce((sum, t) => {
      if (t.running) return sum + timerSeconds;
      return sum + t.total_seconds;
    }, 0);
  };

  const createMutation = useMutation({
    mutationFn: () => api.tickets.create(form),
    onSuccess: () => {
      toast.success('Ticket created');
      setShowForm(false);
      setForm({
        customer_id: '',
        title: '',
        description: '',
        device_type: '',
        device_model: '',
        device_serial: '',
        device_imei: '',
        device_password: '',
        priority: 'medium',
      });
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
    onError: () => toast.error('Failed to create ticket'),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.tickets.updateStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tickets'] }),
  });

  const viewTicket = async (t: Ticket) => {
    setSelectedTicket(t);
    setNewNote('');
    loadTimers(t.id);
    loadChecklist(t.id);
    loadTemplates();
  };

  const loadChecklist = async (ticketId: string) => {
    try {
      const res = await api.checklist.ticket.list(ticketId);
      setChecklist(res.items);
    } catch {
      setChecklist([]);
    }
  };

  const loadTemplates = async () => {
    try {
      const res = await api.checklist.templates.list();
      setChecklistTemplates(res.templates);
    } catch {
      setChecklistTemplates([]);
    }
  };

  const handleApplyTemplate = async (templateId: string) => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.apply(selectedTicket.id, templateId);
      toast.success('Checklist applied');
      setShowApplyTemplate(false);
      loadChecklist(selectedTicket.id);
    } catch {
      toast.error('Failed to apply checklist');
    }
  };

  const handleToggleChecklist = async (item: TicketChecklistItem) => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.toggle(selectedTicket.id, item.id, !item.completed);
      loadChecklist(selectedTicket.id);
    } catch {
      toast.error('Failed to update checklist item');
    }
  };

  const handleClearChecklist = async () => {
    if (!selectedTicket) return;
    try {
      await api.checklist.ticket.clear(selectedTicket.id);
      toast.success('Checklist cleared');
      setChecklist([]);
    } catch {
      toast.error('Failed to clear checklist');
    }
  };

  const noteMutation = useMutation({
    mutationFn: ({ ticketId, content }: { ticketId: string; content: string }) =>
      api.tickets.notes.create(ticketId, {
        author: 'User',
        content,
        internal: false,
      }),
    onSuccess: (_, { ticketId }) => {
      setNewNote('');
      queryClient.invalidateQueries({ queryKey: ['ticket-notes', ticketId] });
    },
    onError: () => toast.error('Failed to add note'),
  });

  const addNote = () => {
    if (!newNote.trim() || !selectedTicket) return;
    noteMutation.mutate({ ticketId: selectedTicket.id, content: newNote });
  };

  return (
    <>
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-2xl font-bold">Tickets</h1>
          {breachCount > 0 && (
            <Badge variant="destructive" className="text-xs animate-pulse">
              <AlertTriangle className="h-3 w-3 mr-1" />
              {breachCount} SLA breach{breachCount !== 1 ? 'es' : ''}
            </Badge>
          )}
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-1.5" /> New Ticket
        </Button>
      </div>
      <p className="text-sm text-muted-foreground -mt-2">Manage repair tickets</p>

      <div className="flex gap-2 flex-wrap">
        {['', 'new', 'assigned', 'in_progress', 'waiting_on_customer', 'resolved', 'closed'].map(
          (s) => (
            <Button
              key={s}
              size="sm"
              variant={filter === s ? 'default' : 'outline'}
              onClick={() => handleFilter(s)}
            >
              {s || 'All'}
            </Button>
          ),
        )}
      </div>

      {showForm && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle>New Ticket</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
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
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <div className="grid grid-cols-5 gap-2">
              <Input
                placeholder="Device type"
                value={form.device_type}
                onChange={(e) => setForm({ ...form, device_type: e.target.value })}
              />
              <Input
                placeholder="Device model"
                value={form.device_model}
                onChange={(e) => setForm({ ...form, device_model: e.target.value })}
              />
              <Input
                placeholder="Serial"
                value={form.device_serial}
                onChange={(e) => setForm({ ...form, device_serial: e.target.value })}
              />
              <Input
                placeholder="IMEI"
                value={form.device_imei}
                onChange={(e) => setForm({ ...form, device_imei: e.target.value })}
              />
              <Input
                placeholder="Password"
                value={form.device_password}
                onChange={(e) => setForm({ ...form, device_password: e.target.value })}
              />
            </div>
            <Select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </Select>
            <div className="flex gap-2">
              <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
                Create
              </Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ticket list & detail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`space-y-3 ${selectedTicket ? 'hidden lg:block' : ''}`}>
          {tickets.map((t) => {
            const cust = customers.find((c) => c.id === t.customer_id);
            return (
              <Card
                key={t.id}
                className={`cursor-pointer transition-colors ${selectedTicket?.id === t.id ? 'border-primary' : 'hover:border-primary/30'} ${breachedIds.has(t.id) ? 'border-l-red-500 border-l-4' : ''}`}
                onClick={() => viewTicket(t)}
              >
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">#{t.ticket_number}</span>
                        <Badge variant={statusColors[t.status] || 'secondary'}>{t.status}</Badge>
                        <span className={`text-xs ${priorityColors[t.priority] || ''}`}>
                          {t.priority}
                        </span>
                        <span
                          className="ml-auto flex items-center gap-1"
                          title={new Date(t.created_at).toLocaleString()}
                        >
                          <span
                            className={`inline-block h-2 w-2 rounded-full ${slaUrgency(t.created_at).color}`}
                          />
                          <span className="text-[10px] text-muted-foreground">
                            {slaUrgency(t.created_at).label}
                          </span>
                        </span>
                      </div>
                      <p className="font-medium mt-1 truncate">{t.title}</p>
                      {cust && (
                        <p className="text-xs text-muted-foreground">
                          {cust.first_name} {cust.last_name}
                        </p>
                      )}
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
            {/* Back button (mobile) */}
            <button
              onClick={() => setSelectedTicket(null)}
              className="lg:hidden text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              ← Back to list
            </button>
            <Card>
              <CardHeader>
                <CardTitle>
                  #{selectedTicket.ticket_number} — {selectedTicket.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {selectedTicket.description || 'No description'}
                </p>
                {selectedTicket.device_type && (
                  <p className="text-xs text-muted-foreground">
                    Device: {selectedTicket.device_type} {selectedTicket.device_model} (
                    {selectedTicket.device_serial})
                    {selectedTicket.device_imei && <span> IMEI: {selectedTicket.device_imei}</span>}
                    {selectedTicket.device_password && (
                      <span> PWD: {selectedTicket.device_password}</span>
                    )}
                  </p>
                )}
                <Select
                  value={selectedTicket.status}
                  onChange={(e) =>
                    statusMutation.mutate({
                      id: selectedTicket.id,
                      status: e.target.value,
                    })
                  }
                >
                  <option value="new">New</option>
                  <option value="assigned">Assigned</option>
                  <option value="in_progress">In Progress</option>
                  <option value="waiting_on_customer">Waiting on Customer</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </Select>
                <div className="flex gap-2 mt-2">
                  {selectedTicket.estimate_id && (
                    <a
                      href={`/estimates/${selectedTicket.estimate_id}`}
                      className="text-xs text-primary underline"
                    >
                      Estimate #{selectedTicket.estimate_id}
                    </a>
                  )}
                  {selectedTicket.invoice_id && (
                    <a
                      href={`/invoices/${selectedTicket.invoice_id}`}
                      className="text-xs text-primary underline"
                    >
                      Invoice #{selectedTicket.invoice_id}
                    </a>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Timer */}
            <Card>
              <CardHeader>
                <CardTitle>
                  <Timer className="h-4 w-4 inline mr-1.5" />
                  Time Tracking
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-2xl font-mono font-bold">
                      {fmtTime(totalTrackedTime())}
                    </span>
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
                    {timers
                      .slice()
                      .reverse()
                      .map((tmr) => (
                        <div
                          key={tmr.id}
                          className="flex items-center justify-between text-xs p-2 rounded bg-muted/50"
                        >
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
                  <CardTitle>
                    <ListChecks className="h-4 w-4 inline mr-1.5" />
                    Checklist
                  </CardTitle>
                  <div className="flex gap-1">
                    {checklist.some((i) => i.template_id) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={handleClearChecklist}
                      >
                        Clear
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setShowApplyTemplate(!showApplyTemplate)}
                    >
                      Apply Template
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {showApplyTemplate && (
                  <div className="mb-3 p-2 rounded bg-muted/50 space-y-1">
                    <p className="text-xs font-medium text-muted-foreground mb-1">
                      Choose a template:
                    </p>
                    {checklistTemplates.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        No templates available. Create one in Settings.
                      </p>
                    ) : (
                      checklistTemplates.map((t) => (
                        <Button
                          key={t.id}
                          variant="outline"
                          size="sm"
                          className="w-full justify-start text-xs h-7"
                          onClick={() => handleApplyTemplate(t.id)}
                        >
                          <ListChecks className="h-3 w-3 mr-1.5" />
                          {t.name}
                        </Button>
                      ))
                    )}
                  </div>
                )}
                {checklist.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No checklist items
                  </p>
                ) : (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {checklist.map((item) => (
                      <div
                        key={item.id}
                        className={`flex items-center gap-3 px-2 py-1.5 rounded cursor-pointer text-sm transition-colors hover:bg-muted/50 ${item.completed ? 'text-muted-foreground line-through' : ''}`}
                        onClick={() => handleToggleChecklist(item)}
                      >
                        <div
                          className={`w-4 h-4 rounded border-2 shrink-0 flex items-center justify-center transition-colors ${item.completed ? 'bg-primary border-primary' : 'border-muted-foreground/40'}`}
                        >
                          {item.completed && <div className="w-2 h-2 rounded-sm bg-white" />}
                        </div>
                        <span className="flex-1">{item.label}</span>
                        {item.template_name && (
                          <span className="text-[10px] text-muted-foreground shrink-0">
                            {item.template_name}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  {checklist.filter((i) => i.completed).length}/{checklist.length} completed
                </p>
              </CardContent>
            </Card>

            {/* Notes */}
            <Card>
              <CardHeader>
                <CardTitle>
                  <MessageSquare className="h-4 w-4 inline mr-1.5" />
                  Notes
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {notes.map((n) => (
                    <div key={n.id} className="text-sm p-2 rounded bg-muted/50">
                      <p className="text-xs text-muted-foreground">
                        {n.author} — {new Date(n.created_at).toLocaleString()}
                      </p>
                      <p className="mt-1">{n.content}</p>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="Add note..."
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addNote()}
                  />
                  <Button size="sm" onClick={addNote}>
                    Send
                  </Button>
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

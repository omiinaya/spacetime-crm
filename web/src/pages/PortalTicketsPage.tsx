import { useState, useEffect } from "react";
import { portalApi, PortalTicket } from "../lib/portal-auth";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { toast } from "sonner";
import { ChevronDown, ChevronUp, MessageSquare } from "lucide-react";

const statusColors: Record<string, "outline" | "default" | "success" | "destructive"> = {
  new: "default",
  in_progress: "default",
  waiting_parts: "outline",
  waiting_customer: "outline",
  resolved: "success",
  closed: "outline",
};

export default function PortalTicketsPage() {
  const [tickets, setTickets] = useState<PortalTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<PortalTicket | null>(null);
  const [noteText, setNoteText] = useState("");
  const [sending, setSending] = useState(false);

  const load = async () => {
    try {
      const res = await portalApi.tickets.list();
      setTickets(res.tickets);
    } catch { toast.error("Failed to load tickets"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const toggleDetail = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    try {
      const res = await portalApi.tickets.get(id);
      setDetail(res.ticket);
    } catch { toast.error("Failed to load ticket"); }
  };

  const addNote = async (ticketId: string) => {
    if (!noteText.trim()) return;
    setSending(true);
    try {
      await portalApi.tickets.addNote(ticketId, noteText);
      toast.success("Note added");
      setNoteText("");
      // Reload detail
      const res = await portalApi.tickets.get(ticketId);
      setDetail(res.ticket);
    } catch { toast.error("Failed to add note"); }
    finally { setSending(false); }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold">My Tickets</h1>
      <p className="text-sm text-muted-foreground mt-1">Track your service requests and repairs</p>

      <div className="space-y-2 mt-4">
        {tickets.map((t) => (
          <Card key={t.id}>
            <CardContent className="pt-4">
              <div className="flex items-start justify-between cursor-pointer" onClick={() => toggleDetail(t.id)}>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{t.ticket_number}</span>
                    <Badge variant={statusColors[t.status] || "outline"}>{t.status.replace(/_/g, " ")}</Badge>
                    <Badge variant="outline" className="text-xs">{t.priority}</Badge>
                  </div>
                  <p className="font-medium mt-1">{t.title}</p>
                  <p className="text-sm text-muted-foreground">
                    {t.device_type} {t.device_model}{t.assigned_name ? ` — ${t.assigned_name}` : ""}
                  </p>
                </div>
                {expanded === t.id ? <ChevronUp className="h-4 w-4 mt-1" /> : <ChevronDown className="h-4 w-4 mt-1" />}
              </div>

              {expanded === t.id && detail && (
                <div className="mt-4 border-t pt-4 space-y-3">
                  <p className="text-sm">{detail.description}</p>

                  {/* Notes */}
                  {detail.notes && detail.notes.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-semibold flex items-center gap-1">
                        <MessageSquare className="h-3.5 w-3.5" /> Updates
                      </p>
                      {detail.notes.map((n) => (
                        <div key={n.id} className="bg-muted/50 rounded p-2 text-sm">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground">{n.author}</span>
                            <span>{new Date(n.created_at).toLocaleDateString()}</span>
                          </div>
                          <p className="mt-1">{n.content}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Add note */}
                  <div className="flex gap-2">
                    <Input placeholder="Add a note..." value={noteText}
                      onChange={(e) => setNoteText(e.target.value)} />
                    <Button size="sm" onClick={() => addNote(t.id)} disabled={sending || !noteText.trim()}>
                      Send
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {!loading && tickets.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">No tickets yet</p>
        )}
      </div>
    </div>
  );
}

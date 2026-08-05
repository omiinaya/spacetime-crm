import { useState, useEffect } from 'react';
import { portalApi, PortalEstimate } from '../lib/portal-auth';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { CheckCircle2, ChevronDown, ChevronUp, XCircle } from 'lucide-react';

const statusColors: Record<string, 'outline' | 'default' | 'success' | 'destructive'> = {
  draft: 'outline',
  sent: 'default',
  pending: 'default',
  approved: 'success',
  declined: 'destructive',
};

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  sent: 'Sent',
  pending: 'Pending',
  approved: 'Approved',
  declined: 'Declined',
};

function canDecide(est: PortalEstimate) {
  return !['approved', 'declined'].includes(est.status || '');
}

export default function PortalEstimatesPage() {
  const [estimates, setEstimates] = useState<PortalEstimate[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<PortalEstimate | null>(null);
  const [acting, setActing] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await portalApi.estimates.list();
      setEstimates(res.estimates);
    } catch {
      toast.error('Failed to load estimates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggleDetail = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    try {
      const res = await portalApi.estimates.get(id);
      setDetail(res.estimate);
    } catch {
      toast.error('Failed to load estimate details');
    }
  };

  const decide = async (id: string, status: 'approved' | 'declined') => {
    setActing(id);
    try {
      await portalApi.estimates.setStatus(id, status);
      toast.success(status === 'approved' ? 'Estimate approved — thank you!' : 'Estimate declined');
      // Refresh both list and open detail so statuses stay in sync
      const res = await portalApi.estimates.list();
      setEstimates(res.estimates);
      if (expanded === id) {
        const det = await portalApi.estimates.get(id);
        setDetail(det.estimate);
      }
    } catch (e: unknown) {
      toast.error((e as Error)?.message || 'Failed to update estimate');
    } finally {
      setActing(null);
    }
  };

  const fmtMoney = (v: number | undefined | null) => `$${(v ?? 0).toFixed(2)}`;

  return (
    <div>
      <h1 className="text-2xl font-bold">My Estimates</h1>
      <p className="text-sm text-muted-foreground mt-1">
        Review and approve or decline your estimates
      </p>

      <div className="space-y-2 mt-4">
        {estimates.map((est) => (
          <Card key={est.id}>
            <CardContent className="pt-4">
              <div
                className="flex items-start justify-between cursor-pointer"
                onClick={() => toggleDetail(est.id)}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{est.estimate_number}</span>
                    <Badge variant={statusColors[est.status] || 'outline'}>
                      {STATUS_LABELS[est.status] || est.status}
                    </Badge>
                  </div>
                  <p className="font-medium mt-1">
                    {fmtMoney(est.total)}
                    {est.currency && est.currency !== 'USD' && (
                      <span className="text-xs text-muted-foreground ml-1">{est.currency}</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(est.created_at).toLocaleDateString()}
                  </p>
                </div>
                {expanded === est.id ? (
                  <ChevronUp className="h-4 w-4 mt-1" />
                ) : (
                  <ChevronDown className="h-4 w-4 mt-1" />
                )}
              </div>

              {expanded === est.id && detail && (
                <div className="mt-4 border-t pt-4 space-y-3">
                  {/* Line items */}
                  {detail.line_items && detail.line_items.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold mb-2">Items</p>
                      {detail.line_items.map((item) => (
                        <div
                          key={item.id}
                          className="flex justify-between text-sm py-1 border-b border-muted last:border-0"
                        >
                          <span>{item.description}</span>
                          <span className="text-muted-foreground">
                            {item.quantity} × {fmtMoney(item.unit_price)} = {fmtMoney(item.total)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Summary */}
                  <div className="text-sm space-y-1">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Subtotal</span>
                      <span>{fmtMoney(detail.subtotal)}</span>
                    </div>
                    {detail.discount_amount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Discount</span>
                        <span>-{fmtMoney(detail.discount_amount)}</span>
                      </div>
                    )}
                    {detail.tax_amount > 0 && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Tax</span>
                        <span>{fmtMoney(detail.tax_amount)}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-bold text-base border-t pt-1">
                      <span>Total</span>
                      <span>{fmtMoney(detail.total)}</span>
                    </div>
                  </div>

                  {/* Approve / decline */}
                  {canDecide(detail) && (
                    <div className="flex gap-2 pt-1">
                      <Button
                        className="flex-1"
                        disabled={acting === est.id}
                        onClick={() => decide(est.id, 'approved')}
                      >
                        <CheckCircle2 className="h-4 w-4 mr-1.5" />
                        {acting === est.id ? 'Saving...' : 'Approve'}
                      </Button>
                      <Button
                        className="flex-1"
                        variant="outline"
                        disabled={acting === est.id}
                        onClick={() => decide(est.id, 'declined')}
                      >
                        <XCircle className="h-4 w-4 mr-1.5" />
                        Decline
                      </Button>
                    </div>
                  )}

                  {detail.status === 'approved' && (
                    <div className="flex items-center gap-2 text-green-600 text-sm font-medium py-2">
                      <CheckCircle2 className="h-4 w-4" /> Approved
                    </div>
                  )}
                  {detail.status === 'declined' && (
                    <div className="flex items-center gap-2 text-red-500 text-sm font-medium py-2">
                      <XCircle className="h-4 w-4" /> Declined
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {!loading && estimates.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">No estimates yet</p>
        )}
      </div>
    </div>
  );
}

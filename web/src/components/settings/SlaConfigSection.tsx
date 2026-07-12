import { Loader2, Shield, ShieldAlert } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../../lib/query-client';
import { api } from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';

export default function SlaConfigSection() {
  const [targets, setTargets] = useState<Record<string, number>>({
    urgent: 4,
    high: 24,
    medium: 72,
    low: 120,
  });
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['sla-settings'],
    queryFn: async () => {
      const res = await api.tickets.sla.settings();
      setTargets(res.targets);
      return res;
    },
  });

  const saveMutation = useMutation({
    mutationFn: (t: Record<string, number>) => api.tickets.sla.save(t),
    onSuccess: () => {
      toast.success('SLA targets saved');
      setEditing(false);
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ['sla-settings'] });
      queryClient.invalidateQueries({ queryKey: ['tickets', 'sla-breaches'] });
    },
    onError: () => {
      toast.error('Failed to save SLA targets');
    },
  });

  const handleChange = (key: string, raw: string) => {
    const val = parseFloat(raw);
    if (!isNaN(val) && val > 0) {
      setTargets((prev) => ({ ...prev, [key]: val }));
      setDirty(true);
    }
  };

  const labelMap: Record<string, string> = {
    urgent: 'Urgent',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
  };

  const helpMap: Record<string, string> = {
    urgent: 'Response expected within 4 hours',
    high: 'Response expected within 24 hours',
    medium: 'Response expected within 3 days',
    low: 'Response expected within 5 days',
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" />
          SLA Targets
        </CardTitle>
        {!editing ? (
          <Button size="sm" onClick={() => setEditing(true)} disabled={isLoading}>
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setTargets(
                  data?.targets ?? {
                    urgent: 4,
                    high: 24,
                    medium: 72,
                    low: 120,
                  },
                );
                setEditing(false);
                setDirty(false);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => saveMutation.mutate(targets)}
              disabled={!dirty || saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
              Save
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Thresholds in hours after which a ticket is considered breaching SLA. Changes take effect
          immediately on the next SLA breach scan (auto-refresh every 60s).
        </p>
        <div className="space-y-4">
          {['urgent', 'high', 'medium', 'low'].map((key) => (
            <div key={key} className="flex items-center gap-4">
              <label className="w-24 text-sm font-medium text-right">{labelMap[key]}</label>
              {editing ? (
                <Input
                  type="number"
                  min={1}
                  max={8760}
                  value={targets[key] ?? ''}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-28"
                />
              ) : (
                <span className="text-sm font-mono tabular-nums w-28">{targets[key] ?? '-'}h</span>
              )}
              <span className="text-xs text-muted-foreground">{helpMap[key]}</span>
            </div>
          ))}
        </div>
        {!editing && data?.updated_at ? (
          <p className="text-xs text-muted-foreground mt-4">
            Last updated: {new Date(data.updated_at).toLocaleString()}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

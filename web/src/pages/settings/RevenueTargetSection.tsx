import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { toast } from 'sonner';
import { DollarSign, Save } from 'lucide-react';
import { queryClient } from '../../lib/query-client';

export default function RevenueTargetSection() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings', 'app'],
    queryFn: () => api.settings.app.get(),
  });

  const [target, setTarget] = useState('25000');

  useEffect(() => {
    if (data?.config?.revenue_target) {
      setTarget(String(data.config.revenue_target));
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: () =>
      api.settings.app.save({ revenue_target: parseFloat(target) || 0 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'app'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      toast.success('Revenue target updated');
    },
    onError: () => toast.error('Failed to save revenue target'),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          Monthly Revenue Target
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Set the monthly revenue goal shown on the dashboard progress bar.
        </p>
        <div className="flex items-center gap-2 max-w-xs">
          <span className="text-sm text-muted-foreground">$</span>
          <Input
            type="number"
            min="0"
            step="100"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="25000"
          />
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || isLoading}
          >
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

import { CheckCircle, Loader2, Mail, Settings, User as UserIcon, XCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../../lib/query-client';
import { api, MailSettings, User } from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';

export default function MailSettingsSection() {
  const [mailConfig, setMailConfig] = useState<MailSettings>({
    host: '',
    port: 587,
    username: '',
    use_tls: true,
    sender_name: 'SpacetimeCRM',
    sender_email: '',
    password: '',
  });
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message?: string;
    error?: string;
  } | null>(null);

  const { data: mailSettingsData } = useQuery({
    queryKey: ['mail-settings'],
    queryFn: () => api.settings.mail.get(),
  });

  const configured = mailSettingsData?.configured ?? false;

  useEffect(() => {
    if (mailSettingsData?.settings) {
      setMailConfig((prev) => ({
        ...prev,
        ...mailSettingsData.settings!,
        password: '',
      }));
    }
  }, [mailSettingsData]);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<MailSettings>) => {
      const payload = { ...data };
      if (!payload.password) delete payload.password;
      return api.settings.mail.save(payload);
    },
    onSuccess: () => {
      toast.success('Mail settings saved');
      queryClient.invalidateQueries({ queryKey: ['mail-settings'] });
    },
    onError: () => {
      toast.error('Failed to save mail settings');
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const saveData = { ...mailConfig };
      if (!saveData.password) delete saveData.password;
      await api.settings.mail.save(saveData);
      return api.settings.mail.test();
    },
    onSuccess: (res) => {
      setTestResult(res);
      if (res.ok) {
        toast.success('SMTP connection successful');
      } else {
        toast.error('SMTP test failed');
      }
      queryClient.invalidateQueries({ queryKey: ['mail-settings'] });
    },
    onError: () => {
      toast.error('Test failed');
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-4 w-4" />
          Email Notifications
          {configured && (
            <Badge variant="success" className="ml-2 text-xs">
              Configured
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Configure SMTP to send email notifications to customers when tickets are updated, invoices
          are created, appointments are scheduled, or payments are received.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">SMTP Host</label>
            <Input
              placeholder="smtp.example.com"
              value={mailConfig.host}
              onChange={(e) => setMailConfig({ ...mailConfig, host: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Port</label>
            <Input
              type="number"
              placeholder="587"
              value={mailConfig.port}
              onChange={(e) => setMailConfig({ ...mailConfig, port: Number(e.target.value) })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Username</label>
            <Input
              placeholder="user@example.com"
              value={mailConfig.username}
              onChange={(e) => setMailConfig({ ...mailConfig, username: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Password</label>
            <Input
              type="password"
              placeholder="••••••••"
              value={mailConfig.password || ''}
              onChange={(e) => setMailConfig({ ...mailConfig, password: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Sender Name</label>
            <Input
              placeholder="SpacetimeCRM"
              value={mailConfig.sender_name}
              onChange={(e) => setMailConfig({ ...mailConfig, sender_name: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Sender Email</label>
            <Input
              placeholder="noreply@example.com"
              value={mailConfig.sender_email}
              onChange={(e) => setMailConfig({ ...mailConfig, sender_email: e.target.value })}
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={mailConfig.use_tls}
            onChange={(e) => setMailConfig({ ...mailConfig, use_tls: e.target.checked })}
            className="rounded border-border"
          />
          Use STARTTLS (recommended)
        </label>

        <div className="flex gap-2">
          <Button onClick={() => saveMutation.mutate(mailConfig)}>Save Settings</Button>
          <Button
            variant="outline"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Connection'
            )}
          </Button>
        </div>

        {testResult && (
          <div
            className={`flex items-center gap-2 text-sm p-3 rounded ${testResult.ok ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-500'}`}
          >
            {testResult.ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            <span>
              {testResult.ok
                ? testResult.message || 'Connected!'
                : testResult.error || 'Connection failed'}
            </span>
          </div>
        )}

        <div className="border-t pt-3">
          <p className="text-xs text-muted-foreground">
            <strong>Notification triggers:</strong> Ticket status changes, new invoices, appointment
            scheduling, payment receipts, and estimate approvals will automatically email the
            customer when mail is configured.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

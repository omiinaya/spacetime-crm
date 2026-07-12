import { CheckCircle, Loader2, Phone, Settings, XCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../../lib/query-client';
import { api, SmsSettings } from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';

export default function SmsSettingsSection() {
  const [smsConfig, setSmsConfig] = useState({
    account_sid: '',
    from_number: '',
    auth_token: '',
  });
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message?: string;
    error?: string;
  } | null>(null);

  const { data: smsSettingsData } = useQuery({
    queryKey: ['sms-settings'],
    queryFn: () => api.settings.sms.get(),
  });

  const configured = smsSettingsData?.configured ?? false;

  useEffect(() => {
    if (smsSettingsData?.settings) {
      setSmsConfig((prev) => ({
        ...prev,
        account_sid: smsSettingsData.settings!.account_sid || '',
        from_number: smsSettingsData.settings!.from_number || '',
      }));
    }
  }, [smsSettingsData]);

  const saveMutation = useMutation({
    mutationFn: (data: { account_sid?: string; auth_token?: string; from_number?: string }) => {
      const payload = { ...data };
      if (!payload.auth_token) payload.auth_token = undefined as any;
      return api.settings.sms.save(payload);
    },
    onSuccess: () => {
      toast.success('SMS settings saved');
      queryClient.invalidateQueries({ queryKey: ['sms-settings'] });
    },
    onError: () => {
      toast.error('Failed to save SMS settings');
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const saveData = { ...smsConfig };
      if (!saveData.auth_token) saveData.auth_token = undefined as any;
      await api.settings.sms.save(saveData);
      return api.settings.sms.test();
    },
    onSuccess: (res) => {
      setTestResult(res);
      if (res.ok) {
        toast.success('Twilio connection successful');
      } else {
        toast.error('Twilio test failed');
      }
      queryClient.invalidateQueries({ queryKey: ['sms-settings'] });
    },
    onError: () => {
      toast.error('Test failed');
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Phone className="h-4 w-4" />
          SMS Notifications (Twilio)
          {configured && (
            <Badge variant="success" className="ml-2 text-xs">
              Configured
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Configure Twilio to send SMS notifications to customers when tickets are updated, invoices
          are created, payments are received, appointments are scheduled, or estimates are approved.
          Messages are sent to the customer's <strong>mobile</strong> phone number.
        </p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Twilio Account SID</label>
            <Input
              placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={smsConfig.account_sid}
              onChange={(e) => setSmsConfig({ ...smsConfig, account_sid: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Auth Token</label>
            <Input
              type="password"
              placeholder="xxxxxxxxxxxxxxxxxxxxxxxx"
              value={smsConfig.auth_token}
              onChange={(e) => setSmsConfig({ ...smsConfig, auth_token: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">From Number</label>
            <Input
              placeholder="+15551234567"
              value={smsConfig.from_number}
              onChange={(e) => setSmsConfig({ ...smsConfig, from_number: e.target.value })}
            />
          </div>
        </div>

        <div className="flex gap-2">
          <Button onClick={() => saveMutation.mutate(smsConfig)}>Save Settings</Button>
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
            <strong>Notification triggers:</strong> Ticket status changes, new invoices, payment
            receipts, appointment scheduling, and estimate approvals will automatically send an SMS
            to the customer's mobile number when Twilio is configured.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

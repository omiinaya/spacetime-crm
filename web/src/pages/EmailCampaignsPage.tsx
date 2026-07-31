import { useState, useCallback } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Send, Loader2, Mail, Users, CheckCircle2, XCircle, TestTube } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../lib/auth';

export default function EmailCampaignsPage() {
  const { token } = useAuth();
  const [subject, setSubject] = useState('');
  const [htmlBody, setHtmlBody] = useState('');
  const [customerFilter, setCustomerFilter] = useState<string>('all');
  const [daysSinceLast, setDaysSinceLast] = useState('30');
  const [testEmail, setTestEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{
    sent: number;
    failed: number;
    total_matched: number;
    mode: string;
    recipients?: string[];
  } | null>(null);

  const templates = [
    {
      name: 'Promotional Offer',
      body: `<h1>Special Offer Just for You, {{name}}!</h1>
<p>We're excited to let you know about our latest deals at SpacetimeCRM.</p>
<p>Visit us today to take advantage of these limited-time offers.</p>
<br>
<p>Thank you for your business,</p>
<p><strong>The SpacetimeCRM Team</strong></p>`,
    },
    {
      name: 'Service Reminder',
      body: `<h1>Service Reminder, {{name}}</h1>
<p>This is a friendly reminder that your device may be due for service or maintenance.</p>
<p>Please contact us to schedule an appointment at your earliest convenience.</p>
<br>
<p>Thank you,</p>
<p><strong>The SpacetimeCRM Team</strong></p>`,
    },
    {
      name: 'Seasonal Greeting',
      body: `<h1>Season's Greetings, {{name}}!</h1>
<p>Warm wishes from all of us at SpacetimeCRM.</p>
<p>We appreciate your continued trust and look forward to serving you in the coming year.</p>
<br>
<p>Happy holidays,</p>
<p><strong>The SpacetimeCRM Team</strong></p>`,
    },
  ];

  const handleSend = useCallback(
    async (isTest: boolean) => {
      if (!subject.trim()) {
        toast.error('Subject is required');
        return;
      }
      if (!htmlBody.trim()) {
        toast.error('Email body is required');
        return;
      }

      if (isTest && !testEmail.trim()) {
        toast.error('Enter a test email address');
        return;
      }

      setSending(true);
      setResult(null);
      try {
        const res = await fetch('/api/email-campaigns/send-blast', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            subject: subject.trim(),
            html_body: htmlBody.trim(),
            customer_filter: customerFilter,
            days_since_last: parseInt(daysSinceLast) || 30,
            ...(isTest ? { send_test_only: testEmail.trim() } : {}),
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.detail || 'Failed to send');
          return;
        }
        setResult(data);
        toast.success(isTest ? 'Test email sent' : `Campaign sent to ${data.sent} recipient(s)`);
      } catch {
        toast.error('Network error');
      } finally {
        setSending(false);
      }
    },
    [subject, htmlBody, customerFilter, daysSinceLast, testEmail, token],
  );

  return (
    <div className="p-4 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Mail className="w-5 h-5" /> Email Campaigns
        </h2>
      </div>

      {/* ── Compose ── */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Send className="w-4 h-4" /> Compose Email Blast
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Subject</label>
            <Input
              placeholder="Email subject line"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs text-muted-foreground">HTML Body</label>
              <div className="flex gap-1">
                {templates.map((t) => (
                  <Button
                    key={t.name}
                    variant="ghost"
                    size="sm"
                    className="text-xs"
                    onClick={() => setHtmlBody(t.body)}
                  >
                    {t.name}
                  </Button>
                ))}
              </div>
            </div>
            <Textarea
              placeholder="<h1>Hello {{name}}!</h1><p>Your message here...</p>"
              value={htmlBody}
              onChange={(e) => setHtmlBody(e.target.value)}
              className="min-h-[200px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Use {'{{name}}'} for customer name and {'{{email}}'} for email address.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Customer Filter</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={customerFilter}
                onChange={(e) => setCustomerFilter(e.target.value)}
              >
                <option value="all">All customers with email</option>
                <option value="with_email">Has email</option>
                <option value="recent">Recent activity</option>
              </select>
            </div>
            {customerFilter === 'recent' && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  Days since last ticket
                </label>
                <Input
                  type="number"
                  min="1"
                  value={daysSinceLast}
                  onChange={(e) => setDaysSinceLast(e.target.value)}
                />
              </div>
            )}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Test Email</label>
              <div className="flex gap-1">
                <Input
                  placeholder="test@example.com"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={sending || !testEmail.trim()}
                  onClick={() => handleSend(true)}
                >
                  {sending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <TestTube className="w-3 h-3" />
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button
              variant="default"
              size="lg"
              disabled={sending || !subject.trim() || !htmlBody.trim()}
              onClick={() => {
                if (
                  !confirm(
                    `Send this email blast to all matching customers? This cannot be undone.`,
                  )
                )
                  return;
                handleSend(false);
              }}
            >
              {sending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Send className="w-4 h-4 mr-2" />
              )}
              Send Blast
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ── Result ── */}
      {result && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              {result.mode === 'test' ? (
                <TestTube className="w-4 h-4" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              )}
              Campaign Result
              <Badge variant={result.failed === 0 ? 'default' : 'destructive'}>
                {result.mode === 'test' ? 'Test' : 'Live'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-6 text-sm">
              <div>
                <p className="text-muted-foreground">Matched</p>
                <p className="text-lg font-bold">{result.total_matched}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Sent</p>
                <p className="text-lg font-bold text-green-600">{result.sent}</p>
              </div>
              {result.failed > 0 && (
                <div>
                  <p className="text-muted-foreground">Failed</p>
                  <p className="text-lg font-bold text-red-600">{result.failed}</p>
                </div>
              )}
            </div>
            {result.recipients && result.recipients.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-muted-foreground mb-1">
                  First {result.recipients.length} recipients:
                </p>
                <div className="flex flex-wrap gap-1">
                  {result.recipients.map((r) => (
                    <Badge key={r} variant="outline" className="text-xs">
                      {r}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

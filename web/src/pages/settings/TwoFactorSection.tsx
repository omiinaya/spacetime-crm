import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../../lib/query-client';
import {
  api,
  WebhookSubscription,
  User,
  MailSettings,
  SmsSettings,
  BusinessHours,
} from '../../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { Badge } from '../../components/ui/badge';
import {
  Settings,
  Plus,
  Mail,
  CheckCircle,
  XCircle,
  Loader2,
  Percent,
  Webhook,
  Globe,
  Trash2,
  Play,
  Phone,
  Smartphone,
  Shield,
  ShieldAlert,
  Palette,
  Sun,
  Moon,
  Clock,
  User as UserIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../lib/auth';
import { useTheme } from '../../lib/theme';

export default function TwoFactorSection() {
  const { user, token } = useAuth();
  const [step, setStep] = useState<'idle' | 'setup' | 'verify'>('idle');
  const [secret, setSecret] = useState('');
  const [provisioningUri, setProvisioningUri] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showDisable, setShowDisable] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setIsEnrolled(data.totp_enabled ?? false);
      } catch {}
    };
    if (token) check();
  }, [token]);

  if (!user) return null;

  const handleSetup = async () => {
    setBusy(true);
    try {
      const res = await fetch('/api/auth/setup-2fa', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Setup failed');
        return;
      }
      const data = await res.json();
      setSecret(data.secret);
      setProvisioningUri(data.provisioning_uri);
      setStep('verify');
    } catch (e: unknown) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async () => {
    if (verifyCode.length !== 6) return;
    setBusy(true);
    try {
      const res = await fetch('/api/auth/verify-2fa', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: verifyCode }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Verification failed');
        return;
      }
      toast.success('2FA enabled successfully');
      setIsEnrolled(true);
      setStep('idle');
      setSecret('');
      setVerifyCode('');
    } catch (e: unknown) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async () => {
    if (disableCode.length !== 6) return;
    setBusy(true);
    try {
      const res = await fetch('/api/auth/disable-2fa', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: disableCode }),
      });
      if (!res.ok) {
        const err = await res.json();
        toast.error(err.detail || 'Disable failed');
        return;
      }
      toast.success('2FA disabled');
      setIsEnrolled(false);
      setShowDisable(false);
      setDisableCode('');
    } catch (e: unknown) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-4 h-4" /> Two-Factor Authentication
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isEnrolled ? (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-500">2FA is enabled</span>
            </div>
            {!showDisable ? (
              <Button variant="outline" size="sm" onClick={() => setShowDisable(true)}>
                Disable 2FA
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Enter a current 2FA code from your authenticator app to disable.
                </p>
                <div className="flex gap-2">
                  <Input
                    placeholder="000000"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="w-32 font-mono text-center"
                    maxLength={6}
                  />
                  <Button
                    size="sm"
                    onClick={handleDisable}
                    disabled={busy || disableCode.length !== 6}
                  >
                    {busy ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                    Disable
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setShowDisable(false);
                      setDisableCode('');
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : step === 'idle' ? (
          <div>
            <p className="text-sm text-muted-foreground mb-3">
              Add an extra layer of security to your account by enabling two-factor authentication.
            </p>
            <Button size="sm" onClick={handleSetup} disabled={busy}>
              {busy ? (
                <Loader2 className="w-3 h-3 animate-spin mr-1" />
              ) : (
                <Smartphone className="w-3 h-3 mr-1" />
              )}
              Set up 2FA
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm font-medium">Step 1: Scan this QR code</p>
            <p className="text-xs text-muted-foreground">
              Use your authenticator app (Google Authenticator, Authy, etc.) to scan the QR code
              below.
            </p>
            <div className="flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`}
                alt="2FA QR Code"
                className="border rounded-lg"
                style={{ imageRendering: 'pixelated' }}
              />
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground">Or enter this key manually:</p>
              <code className="text-xs bg-muted px-2 py-1 rounded select-all">{secret}</code>
            </div>
            <div className="border-t pt-3">
              <p className="text-sm font-medium mb-2">Step 2: Verify the code</p>
              <div className="flex gap-2">
                <Input
                  placeholder="000000"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className="w-32 font-mono text-center"
                  maxLength={6}
                  autoFocus
                />
                <Button size="sm" onClick={handleVerify} disabled={busy || verifyCode.length !== 6}>
                  {busy ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                  Verify & Enable
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setStep('idle')}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

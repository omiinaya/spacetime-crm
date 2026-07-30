import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient } from "../../lib/query-client";
import {
  api,
  WebhookSubscription,
  User,
  MailSettings,
  SmsSettings,
  BusinessHours,
} from "../../lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { Badge } from "../../components/ui/badge";
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
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../lib/auth";
import { useTheme } from "../../lib/theme";

export default function PinSection() {
  const { user, token } = useAuth();
  const [pin, setPin] = useState("");
  const [confirmPin, setConfirmPin] = useState("");
  const [busy, setBusy] = useState(false);
  const [hasPin, setHasPin] = useState<boolean | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setHasPin(data.has_pin ?? false))
      .catch(() => setHasPin(false));
  }, [token]);

  if (!user) return null;

  const handleSetPin = async () => {
    if (!pin || pin.length < 4 || pin.length > 10) {
      toast.error("PIN must be 4–10 digits");
      return;
    }
    if (pin !== confirmPin) {
      toast.error("PINs do not match");
      return;
    }
    setBusy(true);
    try {
      await api.auth.setPin(pin);
      toast.success("POS PIN set successfully");
      setPin("");
      setConfirmPin("");
      setHasPin(true);
    } catch (e: unknown) {
      toast.error((e as Error).message || "Failed to set PIN");
    } finally {
      setBusy(false);
    }
  };

  const handleRemovePin = async () => {
    setBusy(true);
    try {
      await api.auth.setPin("");
      toast.success("POS PIN removed");
      setHasPin(false);
    } catch (e: unknown) {
      toast.error((e as Error).message || "Failed to remove PIN");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Smartphone className="h-4 w-4" />
          POS PIN Login
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Set a numeric PIN for quick POS terminal login. PIN is stored as a
          bcrypt hash and used at the POS counter for fast check-in without
          entering your full password.
        </p>
        {hasPin === null ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Checking PIN status...
          </div>
        ) : hasPin ? (
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm">PIN is currently set</span>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleRemovePin}
              disabled={busy}
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                "Remove PIN"
              )}
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2 rounded-md border border-border p-3 text-sm text-muted-foreground">
            <XCircle className="h-4 w-4" />
            No PIN set — POS will skip PIN verification
          </div>
        )}
        <div className="flex gap-2 items-end">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              New PIN (4–10 digits)
            </label>
            <Input
              type="password"
              placeholder="Enter PIN"
              maxLength={10}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">
              Confirm PIN
            </label>
            <Input
              type="password"
              placeholder="Confirm PIN"
              maxLength={10}
              value={confirmPin}
              onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <Button onClick={handleSetPin} disabled={busy || !pin || !confirmPin}>
            {busy ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Saving...
              </>
            ) : (
              "Set PIN"
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

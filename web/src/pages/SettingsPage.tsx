import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { queryClient } from '../lib/query-client';
import {
  api,
  User,
  MailSettings,
  TaxRate,
  WebhookSubscription,
  WEBHOOK_EVENTS,
  SmsSettings,
  BusinessHours,
} from '../lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import {
  Settings,
  Plus,
  User as UserIcon,
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
  Shield,
  ShieldAlert,
  Smartphone,
  Clock,
  Sun,
  Moon,
  Palette,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../lib/auth';
import { useTheme } from '../lib/theme';
import UserSettings from '../components/settings/UserSettings';
import UserPreferencesSection from '../components/settings/UserPreferencesSection';
import MailSettingsSection from '../components/settings/MailSettingsSection';
import SmsSettingsSection from '../components/settings/SmsSettingsSection';
import TaxRateSettings from '../components/settings/TaxRateSettings';
import WebhookSettings from '../components/settings/WebhookSettings';
import PinSection from '../components/settings/PinSection';
import TwoFactorSection from '../components/settings/TwoFactorSection';
import SlaConfigSection from '../components/settings/SlaConfigSection';
import BusinessHoursSection from '../components/settings/BusinessHoursSection';

export default function SettingsPage() {
  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage users and configuration</p>
      </div>
      <UserSettings />
      <UserPreferencesSection />
      <PinSection />
      <TwoFactorSection />
      <MailSettingsSection />
      <SmsSettingsSection />
      <BusinessHoursSection />
      <TaxRateSettings />
      <SlaConfigSection />
      <WebhookSettings />
    </>
  );
}

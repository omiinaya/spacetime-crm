import {
	UserSettings,
	UserPreferencesSection,
	MailSettingsSection,
	SmsSettingsSection,
	BusinessHoursSection,
	TaxRateSettings,
	SlaConfigSection,
	WebhookSettings,
	PinSection,
	TwoFactorSection,
	RevenueTargetSection,
} from "./settings";

export default function SettingsPage() {
	return (
		<>
			<div>
				<h1 className="text-2xl font-bold">Settings</h1>
				<p className="text-sm text-muted-foreground mt-1">
					Manage users and configuration
				</p>
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
			<RevenueTargetSection />
			<WebhookSettings />
		</>
	);
}

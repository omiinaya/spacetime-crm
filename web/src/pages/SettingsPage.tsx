import { useState } from "react";
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
	ReminderScheduleSection,
} from "./settings";
import ImportExportPage from "./ImportExportPage";
import CustomFieldsPage from "./CustomFieldsPage";
import AuditLogPage from "./AuditLogPage";
import HealthPage from "./HealthPage";
import ChecklistTemplatesPage from "./ChecklistTemplatesPage";
import TenantsPage from "./TenantsPage";
import AgentAccessPage from "./AgentAccess";
import { Tabs } from "../components/ui/tabs";

type SettingsTab = "general" | "notifications" | "business" | "data" | "system";

const TABS: { id: SettingsTab; label: string }[] = [
	{ id: "general", label: "General" },
	{ id: "notifications", label: "Notifications" },
	{ id: "business", label: "Business" },
	{ id: "data", label: "Data & Fields" },
	{ id: "system", label: "System" },
];

export default function SettingsPage() {
	const [tab, setTab] = useState<SettingsTab>("general");

	return (
		<>
			<div>
				<h1 className="text-2xl font-bold">Settings</h1>
				<p className="text-sm text-muted-foreground mt-1">
					Manage users and configuration
				</p>
			</div>

			<Tabs
				tabs={TABS}
				active={tab}
				onChange={(id) => setTab(id as SettingsTab)}
			/>

			{tab === "general" && (
				<>
					<UserSettings />
					<UserPreferencesSection />
					<PinSection />
					<TwoFactorSection />
				</>
			)}

			{tab === "notifications" && (
				<>
					<MailSettingsSection />
					<SmsSettingsSection />
					<ReminderScheduleSection />
					<WebhookSettings />
				</>
			)}

			{tab === "business" && (
				<>
					<BusinessHoursSection />
					<TaxRateSettings />
					<SlaConfigSection />
					<RevenueTargetSection />
				</>
			)}

			{tab === "data" && (
				<>
					<ImportExportPage />
					<CustomFieldsPage />
					<AuditLogPage />
				</>
			)}

			{tab === "system" && (
				<>
					<HealthPage />
					<ChecklistTemplatesPage />
					<TenantsPage />
					<AgentAccessPage />
				</>
			)}
		</>
	);
}

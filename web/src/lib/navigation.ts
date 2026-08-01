/**
 * Shared navigation page identifiers.
 *
 * Centralizes the page union so components can type `onNavigate` props
 * without casting through `any` and without duplicating the union per file.
 */
export type PageId =
	| "dashboard"
	| "customers"
	| "tickets"
	| "invoices"
	| "payments"
	| "appointments"
	| "tech-schedule"
	| "products"
	| "estimates"
	| "purchase-orders"
	| "import-export"
	| "audit-log"
	| "pos"
	| "health"
	| "custom-fields"
	| "checklist"
	| "map"
	| "reports"
	| "settings"
	| "tenants"
	| "recurring-invoices"
	| "payment-methods"
	| "gift-cards"
	| "email-campaigns"
	| "agent-access";

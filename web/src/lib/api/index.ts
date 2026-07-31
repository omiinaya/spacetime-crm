// Helpers
export {
	apiFetch,
	buildPaginationParams,
	getApiToken,
	API_BASE,
} from "./client";

// Domain modules
import { stats } from "./stats";
import { customers } from "./customers";
import { checklist } from "./checklist";
import { tickets } from "./tickets";
import { invoices, recurringInvoices } from "./invoices";
import { payments, paymentMethods } from "./payments";
import { appointments } from "./appointments";
import { products } from "./products";
import { estimates } from "./estimates";
import { purchaseOrders } from "./purchase-orders";
import { users, userSettings } from "./users";
import { settings, taxRates } from "./settings";
import { reports, reportSchedules, auditLog } from "./reports";
import { export_ as apiExport } from "./export";
import { health } from "./health";
import { import_ as apiImport } from "./import";
import { tenants } from "./tenants";
import { webhooks } from "./webhooks";
import { pos } from "./pos";
import { auth } from "./auth";
import { customFields } from "./custom-fields";
import { giftCards } from "./gift-cards";

// Combined API client object (mirrors the original api.ts export)
export const api = {
	stats,
	customers,
	checklist,
	tickets,
	invoices,
	payments,
	appointments,
	products,
	estimates,
	purchaseOrders,
	users,
	settings,
	taxRates,
	reports,
	reportSchedules,
	auditLog,
	export: apiExport,
	health,
	customFields,
	import: apiImport,
	tenants,
	webhooks,
	recurringInvoices,
	paymentMethods,
	pos,
	auth,
	userSettings,
	giftCards,
};

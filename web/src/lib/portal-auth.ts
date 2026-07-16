import {
	createContext,
	useContext,
	useState,
	useEffect,
	ReactNode,
	createElement,
} from "react";
import type { SavedPaymentMethod } from "./api-types";

const API_BASE = "/api";

interface PortalCustomer {
	id: string;
	first_name: string;
	last_name: string;
	email: string;
	company: string;
	phone: string;
}

interface PortalAuthState {
	customer: PortalCustomer | null;
	token: string | null;
	loading: boolean;
	login: (email: string, password: string) => Promise<void>;
	logout: () => void;
	setPassword: (password: string) => Promise<void>;
}

const PortalAuthContext = createContext<PortalAuthState | null>(null);

const TOKEN_KEY = "portal_token";
const CUSTOMER_KEY = "portal_customer";

export function PortalAuthProvider({ children }: { children: ReactNode }) {
	const [customer, setCustomer] = useState<PortalCustomer | null>(null);
	const [token, setToken] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const saved = localStorage.getItem(TOKEN_KEY);
		const cust = localStorage.getItem(CUSTOMER_KEY);
		if (saved && cust) {
			setToken(saved);
			setCustomer(JSON.parse(cust));
		}
		setLoading(false);
	}, []);

	const setStored = (tok: string | null, cust: PortalCustomer | null) => {
		if (tok && cust) {
			localStorage.setItem(TOKEN_KEY, tok);
			localStorage.setItem(CUSTOMER_KEY, JSON.stringify(cust));
		} else {
			localStorage.removeItem(TOKEN_KEY);
			localStorage.removeItem(CUSTOMER_KEY);
		}
		setToken(tok);
		setCustomer(cust);
	};

	const login = async (email: string, password: string) => {
		const res = await fetch(`${API_BASE}/portal/login`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password }),
		});
		if (!res.ok) {
			const text = await res.text();
			throw new Error(text);
		}
		const data = await res.json();
		setStored(data.token, data.customer);
	};

	const logout = () => setStored(null, null);

	const setPassword = async (password: string) => {
		if (!token) throw new Error("Not authenticated");
		const res = await fetch(`${API_BASE}/portal/customer/set-password`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Authorization: `Bearer ${token}`,
			},
			body: JSON.stringify({ password }),
		});
		if (!res.ok) {
			const text = await res.text();
			throw new Error(text);
		}
	};

	return createElement(
		PortalAuthContext.Provider,
		{ value: { customer, token, loading, login, logout, setPassword } },
		children,
	);
}

export function usePortalAuth() {
	const ctx = useContext(PortalAuthContext);
	if (!ctx) throw new Error("usePortalAuth must be inside PortalAuthProvider");
	return ctx;
}

export function portalApiFetch<T>(
	path: string,
	options?: RequestInit,
): Promise<T> {
	const token = localStorage.getItem(TOKEN_KEY);
	return fetch(`${API_BASE}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...(token ? { Authorization: `Bearer ${token}` } : {}),
			...options?.headers,
		},
		...options,
	}).then(async (res) => {
		if (!res.ok) {
			const text = await res.text();
			throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
		}
		return res.json();
	});
}

export interface PortalTicket {
	id: string;
	ticket_number: number;
	title: string;
	description: string;
	device_type: string;
	device_model: string;
	status: string;
	priority: string;
	assigned_name: string;
	created_at: number;
	updated_at: number;
	notes?: PortalTicketNote[];
}

export interface PortalTicketNote {
	id: string;
	ticket_id: string;
	author: string;
	content: string;
	created_at: number;
}

export interface PortalInvoice {
	id: string;
	invoice_number: number;
	status: string;
	subtotal: number;
	tax_amount: number;
	total: number;
	notes: string;
	created_at: number;
	due_date: number;
	line_items?: PortalLineItem[];
	payments?: PortalPayment[];
	total_paid?: number;
	balance_due?: number;
}

export interface PortalLineItem {
	id: string;
	description: string;
	quantity: number;
	unit_price: number;
	total: number;
}

export interface PortalPayment {
	id: string;
	amount: number;
	method: string;
	notes: string;
	created_at: number;
}

export interface PortalAppointment {
	id: string;
	title: string;
	description: string;
	start_time: number;
	end_time: number;
	status: string;
}

export interface PortalStats {
	total_tickets: number;
	open_tickets: number;
	total_invoices: number;
	total_billed: number;
	total_paid: number;
	balance_due: number;
	upcoming_appointments: number;
}

export const portalApi = {
	stats: {
		get: () => portalApiFetch<PortalStats>("/portal/stats"),
	},
	tickets: {
		list: () => portalApiFetch<{ tickets: PortalTicket[] }>("/portal/tickets"),
		get: (id: string) =>
			portalApiFetch<{ ticket: PortalTicket }>(`/portal/tickets/${id}`),
		addNote: (id: string, content: string) =>
			portalApiFetch<{ ok: boolean }>(`/portal/tickets/${id}/notes`, {
				method: "POST",
				body: JSON.stringify({ content }),
			}),
	},
	invoices: {
		list: () =>
			portalApiFetch<{ invoices: PortalInvoice[] }>("/portal/invoices"),
		get: (id: string) =>
			portalApiFetch<{ invoice: PortalInvoice }>(`/portal/invoices/${id}`),
	},
	payments: {
		create: (invoiceId: string, amount: number, method: string) =>
			portalApiFetch<{ ok: boolean }>("/portal/payments", {
				method: "POST",
				body: JSON.stringify({ invoice_id: invoiceId, amount, method }),
			}),
		createCheckoutSession: (invoiceId: string) =>
			portalApiFetch<{ session_id: string; url: string }>(
				"/portal/payments/create-checkout-session",
				{
					method: "POST",
					body: JSON.stringify({ invoice_id: invoiceId }),
				},
			),
		payWithSavedCard: (invoiceId: string, paymentMethodId: string) =>
			portalApiFetch<{ ok: boolean; payment_intent_id?: string }>(
				"/portal/payments/pay-with-saved-card",
				{
					method: "POST",
					body: JSON.stringify({
						invoice_id: invoiceId,
						payment_method_id: paymentMethodId,
					}),
				},
			),
	},
	appointments: {
		list: () =>
			portalApiFetch<{
				appointments: PortalAppointment[];
				upcoming: PortalAppointment[];
				past: PortalAppointment[];
			}>("/portal/appointments"),
	},
	paymentMethods: {
		list: () =>
			portalApiFetch<{ payment_methods: SavedPaymentMethod[] }>(
				"/portal/payment-methods",
			),
	},
};

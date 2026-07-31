import {
	createContext,
	useContext,
	useState,
	useEffect,
	ReactNode,
} from "react";

const API_BASE = "/api";

interface AuthUser {
	id: string;
	name: string;
	email: string;
	role: string;
	tenant_id?: string;
	tenant?: Record<string, any>;
}

interface AuthContextType {
	user: AuthUser | null;
	token: string | null;
	loading: boolean;
	login: (email: string, password: string) => Promise<void>;
	complete2FA: (code: string) => Promise<void>;
	logout: () => void;
	refreshTenant: () => Promise<string | null>;
	pending2FA: { tempToken: string; user: Partial<AuthUser> } | null;
}

const AuthContext = createContext<AuthContextType | null>(null);

function getStoredToken(): string | null {
	return localStorage.getItem("crm_token");
}

function storeToken(token: string) {
	localStorage.setItem("crm_token", token);
}

function clearToken() {
	localStorage.removeItem("crm_token");
}

function decodeUser(token: string): AuthUser | null {
	try {
		const payload = JSON.parse(atob(token.split(".")[1]));
		return {
			id: payload.sub,
			name: payload.name,
			email: payload.email,
			role: payload.role,
			tenant_id: payload.tenant_id || "",
		};
	} catch {
		return null;
	}
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const [user, setUser] = useState<AuthUser | null>(null);
	const [token, setToken] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const [pending2FA, setPending2FA] = useState<{
		tempToken: string;
		user: Partial<AuthUser>;
	} | null>(null);

	// Restore session from localStorage on mount
	useEffect(() => {
		const saved = getStoredToken();
		if (saved) {
			const u = decodeUser(saved);
			if (u) {
				setUser(u);
				setToken(saved);
			} else {
				clearToken();
			}
		}
		setLoading(false);
	}, []);

	// Fire-and-forget helper: register push subscription after login
	const trySubscribePush = () => {
		if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
		const token = getStoredToken();
		if (!token) return;
		navigator.serviceWorker.ready
			.then((reg) => {
				reg.pushManager
					.subscribe({
						userVisibleOnly: true,
						applicationServerKey: null, // VAPID public key from server if configured
					})
					.then((sub) => {
						const rawKey = sub.getKey("p256dh");
						const rawAuth = sub.getKey("auth");
						if (!rawKey || !rawAuth) return;
						fetch("/api/push/subscribe", {
							method: "POST",
							headers: {
								"Content-Type": "application/json",
								Authorization: `Bearer ${token}`,
							},
							body: JSON.stringify({
								endpoint: sub.endpoint,
								p256dh_key: btoa(
									String.fromCharCode(...new Uint8Array(rawKey)),
								),
								auth_key: btoa(String.fromCharCode(...new Uint8Array(rawAuth))),
								user_agent: navigator.userAgent,
							}),
						}).catch(() => {});
					})
					.catch(() => {
						// Permission denied or push not supported — not fatal
					});
			})
			.catch(() => {});
	};

	const login = async (email: string, password: string) => {
		setPending2FA(null);
		const res = await fetch(`${API_BASE}/auth/login`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email, password }),
		});
		if (!res.ok) {
			const text = await res.text();
			throw new Error(text.slice(0, 200));
		}
		const data = await res.json();

		if (data.requires_2fa) {
			// Store temp token and show 2FA challenge
			setPending2FA({
				tempToken: data.temp_token,
				user: data.user || { id: data.user_id, name: data.user_name, email },
			});
			return; // Don't complete login yet
		}

		// Normal login
		storeToken(data.token);
		setToken(data.token);
		if (data.user) {
			setUser(data.user);
		} else {
			const u = decodeUser(data.token);
			setUser(u);
		}
		// Subscribe for push notifications after login
		trySubscribePush();
	};

	const complete2FA = async (code: string) => {
		if (!pending2FA) throw new Error("No pending 2FA challenge");
		const res = await fetch(`${API_BASE}/auth/complete-login`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ temp_token: pending2FA.tempToken, code }),
		});
		if (!res.ok) {
			const text = await res.text();
			throw new Error(text.slice(0, 200));
		}
		const data = await res.json();
		storeToken(data.token);
		setToken(data.token);
		if (data.user) {
			setUser(data.user);
		} else {
			const u = decodeUser(data.token);
			setUser(u);
		}
		setPending2FA(null);
	};

	const logout = () => {
		clearToken();
		setToken(null);
		setUser(null);
		setPending2FA(null);
	};

	const refreshTenant = async () => {
		const t = token || getStoredToken();
		if (!t) return null;
		try {
			const res = await fetch(`${API_BASE}/auth/refresh-tenant`, {
				method: "POST",
				headers: { Authorization: `Bearer ${t}` },
			});
			if (!res.ok) return null;
			const data = await res.json();
			storeToken(data.token);
			setToken(data.token);
			const u = decodeUser(data.token);
			if (u) setUser(u);
			return data.tenant_id || null;
		} catch {
			return null;
		}
	};

	return (
		<AuthContext.Provider
			value={{
				user,
				token,
				loading,
				login,
				complete2FA,
				logout,
				refreshTenant,
				pending2FA,
			}}
		>
			{children}
		</AuthContext.Provider>
	);
}

export function useAuth() {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used within AuthProvider");
	return ctx;
}

/** Attach auth headers to fetch calls. Adds Authorization: Bearer if logged in. */
export function authHeaders(token: string | null): Record<string, string> {
	if (!token) return {};
	return { Authorization: `Bearer ${token}` };
}

/** Check if the current user has one of the given roles. */
export function hasRole(
	user: { role?: string } | null,
	...roles: string[]
): boolean {
	if (!user) return false;
	return roles.includes(user.role || "");
}

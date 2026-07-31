import { useState } from "react";
import { useAuth } from "../lib/auth";
import { ShieldAlert } from "lucide-react";

export default function LoginPage() {
	const { login, complete2FA, pending2FA } = useAuth();
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [code, setCode] = useState("");
	const [error, setError] = useState("");
	const [busy, setBusy] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError("");
		setBusy(true);
		try {
			await login(email, password);
		} catch (err: unknown) {
			setError((err as Error).message || "Login failed");
		} finally {
			setBusy(false);
		}
	};

	const handle2FA = async (e: React.FormEvent) => {
		e.preventDefault();
		setError("");
		setBusy(true);
		try {
			await complete2FA(code);
		} catch (err: unknown) {
			setError((err as Error).message || "Verification failed");
		} finally {
			setBusy(false);
		}
	};

	// Show 2FA challenge if pending
	if (pending2FA) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-background">
				<div className="w-full max-w-sm mx-auto p-6">
					<div className="flex flex-col items-center mb-8">
						<div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center mb-4">
							<ShieldAlert className="h-6 w-6 text-white" />
						</div>
						<h1 className="text-xl font-bold">Two-Factor Authentication</h1>
						<p className="text-sm text-muted-foreground mt-1 text-center">
							Enter the 6-digit code from your authenticator app
						</p>
						{pending2FA.user.email && (
							<p className="text-xs text-muted-foreground mt-2">
								{pending2FA.user.email}
							</p>
						)}
					</div>

					<form onSubmit={handle2FA} className="space-y-4">
						<div>
							<input
								type="text"
								inputMode="numeric"
								pattern="[0-9]*"
								maxLength={6}
								value={code}
								onChange={(e) =>
									setCode(e.target.value.replace(/\D/g, "").slice(0, 6))
								}
								placeholder="000000"
								required
								autoFocus
								className="w-full px-3 py-3 rounded-lg border border-border bg-background text-2xl text-center font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary/50"
							/>
						</div>

						{error && (
							<div className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 text-center">
								{error}
							</div>
						)}

						<button
							type="submit"
							disabled={busy || code.length !== 6}
							className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
						>
							{busy ? "Verifying..." : "Verify Code"}
						</button>

						<button
							type="button"
							onClick={() => {
								setCode("");
								setError("");
							}}
							className="w-full py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground transition-colors"
						>
							Back to login
						</button>
					</form>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen flex items-center justify-center bg-background">
			<div className="w-full max-w-sm mx-auto p-6">
				{/* Brand */}
				<div className="flex flex-col items-center mb-8">
					<div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center mb-4">
						<svg
							className="h-6 w-6 text-white"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
							strokeWidth={2}
						>
							<path
								strokeLinecap="round"
								strokeLinejoin="round"
								d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
							/>
						</svg>
					</div>
					<h1 className="text-xl font-bold">SpacetimeCRM</h1>
					<p className="text-sm text-muted-foreground mt-1">
						Sign in to your account
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-4">
					<div>
						<label className="text-sm font-medium mb-1 block">Email</label>
						<input
							type="email"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="admin@repairshop.com"
							required
							className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
						/>
					</div>

					<div>
						<label className="text-sm font-medium mb-1 block">Password</label>
						<input
							type="password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							placeholder="Enter your password"
							required
							minLength={6}
							className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
						/>
					</div>

					{error && (
						<div className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
							{error}
						</div>
					)}

					<button
						type="submit"
						disabled={busy}
						className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
					>
						{busy ? "Signing in..." : "Sign in"}
					</button>
				</form>

				<div className="mt-4 text-center">
					<a
						href="/forgot-password"
						className="text-sm text-muted-foreground hover:text-foreground transition-colors"
					>
						Forgot password?
					</a>
				</div>
			</div>
		</div>
	);
}

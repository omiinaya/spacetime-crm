import { useState } from "react";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
	const [email, setEmail] = useState("");
	const [error, setError] = useState("");
	const [busy, setBusy] = useState(false);
	const [success, setSuccess] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError("");
		setSuccess(false);

		if (!email || !/\S+@\S+\.\S+/.test(email)) {
			setError("Please enter a valid email address.");
			return;
		}

		setBusy(true);
		try {
			const res = await fetch("/api/auth/forgot-password", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email }),
			});

			if (!res.ok) {
				const text = await res.text();
				throw new Error(text.slice(0, 200));
			}

			setSuccess(true);
		} catch (err: unknown) {
			toast.error(
				(err as Error).message || "Something went wrong. Please try again.",
			);
		} finally {
			setBusy(false);
		}
	};

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
					<h1 className="text-xl font-bold">Forgot Password</h1>
					<p className="text-sm text-muted-foreground mt-1">
						Enter your email to receive a reset link
					</p>
				</div>

				{success ? (
					<div className="text-center space-y-4">
						<div className="text-sm text-green-400 bg-green-500/10 rounded-lg px-4 py-3">
							If that email exists, a reset link has been sent.
						</div>
						<a
							href="/"
							className="inline-block text-sm text-primary hover:underline"
						>
							Back to Login
						</a>
					</div>
				) : (
					<form onSubmit={handleSubmit} className="space-y-4">
						<div>
							<label className="text-sm font-medium mb-1 block">Email</label>
							<input
								type="email"
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								placeholder="you@example.com"
								required
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
							{busy ? "Sending..." : "Send Reset Link"}
						</button>

						<div className="text-center">
							<a
								href="/"
								className="text-sm text-muted-foreground hover:text-primary transition-colors"
							>
								Back to Login
							</a>
						</div>
					</form>
				)}
			</div>
		</div>
	);
}

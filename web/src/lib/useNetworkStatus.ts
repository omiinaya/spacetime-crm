/**
 * useNetworkStatus — reactive online/offline detection.
 *
 * Tracks `navigator.onLine` plus the browser `online`/`offline` events so
 * components can show offline state and pages can fall back to cached data.
 */
import { useEffect, useState } from "react";

export function useNetworkStatus(): boolean {
	const [online, setOnline] = useState<boolean>(() =>
		typeof navigator === "undefined" ? true : navigator.onLine,
	);

	useEffect(() => {
		if (typeof window === "undefined") return;
		const goOnline = () => setOnline(true);
		const goOffline = () => setOnline(false);
		window.addEventListener("online", goOnline);
		window.addEventListener("offline", goOffline);
		return () => {
			window.removeEventListener("online", goOnline);
			window.removeEventListener("offline", goOffline);
		};
	}, []);

	return online;
}

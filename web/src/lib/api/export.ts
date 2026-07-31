import { API_BASE, getApiToken } from "./client";

export type ExportFormat = "csv" | "xlsx" | "json";

/**
 * Download an entity export in the given format.
 *
 * Uses fetch + blob so the JWT Authorization header is sent (a plain
 * `<a href>` download cannot carry headers and would 401 on this API).
 */
async function download(entity: string, format: ExportFormat): Promise<void> {
	const token = getApiToken();
	const url = `${API_BASE}/export/${entity}?format=${format}`;
	const res = await fetch(url, {
		headers: token ? { Authorization: `Bearer ${token}` } : {},
	});
	if (!res.ok) {
		const text = await res.text().catch(() => "");
		throw new Error(`Export failed (${res.status}): ${text.slice(0, 200)}`);
	}
	const blob = await res.blob();
	const objectUrl = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = objectUrl;
	a.download = `${entity}.${format}`;
	document.body.appendChild(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(objectUrl);
}

export const export_ = {
	csv: (entity: string) => download(entity, "csv"),
	xlsx: (entity: string) => download(entity, "xlsx"),
	json: (entity: string) => download(entity, "json"),
};

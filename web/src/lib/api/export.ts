import { apiFetch, API_BASE } from "./client";

export const export_ = {
	csv: (entity: string) => {
		const url = `${API_BASE}/export/${entity}`;
		// Trigger download by creating a temporary anchor
		const a = document.createElement("a");
		a.href = url;
		a.download = `${entity}.csv`;
		document.body.appendChild(a);
		a.click();
		a.remove();
	},
};

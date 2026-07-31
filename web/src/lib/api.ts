// Barrel re-exports for backward compatibility
// All types, helpers, and domain APIs are re-exported from here
// so that `import { api, Customer, ... } from "../lib/api"` continues to work.
//
// The domain-split API modules live in ./api/ and are re-exported here.

// Re-export all types from the types module (includes pagination types
// PaginatedResponse / PaginationParams — consolidated from the deleted
// lib/api-types.ts duplicate)
export type * from "./api/types";

// Re-export helpers
export {
	apiFetch,
	buildPaginationParams,
	getApiToken,
	API_BASE,
} from "./api/client";

// Re-export the api client object — import then export to avoid circular alias
import { api as _api } from "./api/index";
export { _api as api };

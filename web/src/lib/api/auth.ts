import { apiFetch, buildPaginationParams } from "./client";

export const auth = {
  setup2FA: () =>
    apiFetch<{ secret: string; provisioning_uri: string }>("/auth/setup-2fa", {
      method: "POST",
    }),
  verify2FA: (code: string) =>
    apiFetch<{ ok: boolean; message: string }>("/auth/verify-2fa", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  disable2FA: (code: string) =>
    apiFetch<{ ok: boolean; message: string }>("/auth/disable-2fa", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  setPin: (pin: string) =>
    apiFetch<{ ok: boolean }>("/auth/set-pin", {
      method: "POST",
      body: JSON.stringify({ pin }),
    }),
  posLogin: (user_id: string, pin: string) =>
    apiFetch<{
      token: string;
      user: {
        id: string;
        name: string;
        email: string;
        role: string;
        tenant_id: string;
      };
    }>("/auth/pos-login", {
      method: "POST",
      body: JSON.stringify({ user_id, pin }),
    }),
};

import type { GiftCard } from './types';
import { apiFetch } from './client';

export interface GiftCardCreatePayload {
  amount: number;
  customer_id?: string;
  customer_name?: string;
  expires_at?: number;
  notes?: string;
}

export interface GiftCardRedeemPayload {
  code: string;
  amount: number;
}

export const giftCards = {
  list: (offset = 0, limit = 50, active?: string) => {
    const p = new URLSearchParams();
    p.set('offset', String(offset));
    p.set('limit', String(limit));
    if (active !== undefined) p.set('active', active);
    return apiFetch<{ gift_cards: GiftCard[]; total: number }>(`/gift-cards?${p}`);
  },

  create: (data: GiftCardCreatePayload) =>
    apiFetch<{ ok: boolean; gift_card: GiftCard }>('/gift-cards', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  lookup: (code: string) =>
    apiFetch<{ gift_card: GiftCard }>(`/gift-cards/lookup?code=${encodeURIComponent(code)}`),

  redeem: (data: GiftCardRedeemPayload) =>
    apiFetch<{ ok: boolean; redeemed: number; remaining: number }>('/gift-cards/redeem', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  void_: (id: string) =>
    apiFetch<{ ok: boolean }>(`/gift-cards/${id}/void`, { method: 'POST' }),
};

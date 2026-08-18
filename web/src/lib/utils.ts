import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format an amount with the given ISO 4217 currency code using Intl.NumberFormat.
 * Falls back to USD when no/invalid currency code is supplied (or Intl is
 * unavailable) so callers never render a bare number.
 */
export function formatCurrency(value: number, currency?: string): string {
  const code = (currency || "USD").toUpperCase();
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: code }).format(value);
  } catch {
    return `$${value.toFixed(2)}`;
  }
}

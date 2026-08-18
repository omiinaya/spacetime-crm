import { describe, it, expect } from "vitest";
import { cn, formatCurrency } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-4", "py-2")).toBe("px-4 py-2");
  });

  it("handles conditional classes", () => {
    expect(cn("base", false && "hidden", "visible")).toBe("base visible");
  });

  it("resolves tailwind conflicts (last wins)", () => {
    expect(cn("px-4", "px-6")).toBe("px-6");
  });

  it("handles undefined and null", () => {
    expect(cn("a", undefined, null, "b")).toBe("a b");
  });

  it("handles empty inputs", () => {
    expect(cn()).toBe("");
  });
});

describe("formatCurrency", () => {
  it("formats USD amounts with the $ symbol", () => {
    expect(formatCurrency(1234.5, "USD")).toBe("$1,234.50");
  });

  it("formats EUR amounts with the € symbol", () => {
    expect(formatCurrency(99, "EUR")).toBe("€99.00");
  });

  it("formats GBP amounts with the £ symbol", () => {
    expect(formatCurrency(50, "GBP")).toBe("£50.00");
  });

  it("defaults to USD when currency is missing", () => {
    expect(formatCurrency(12.34)).toBe("$12.34");
    expect(formatCurrency(12.34, "")).toBe("$12.34");
  });

  it("normalizes lowercase currency codes", () => {
    expect(formatCurrency(10, "eur")).toBe("€10.00");
  });

  it("falls back to a plain dollar format for invalid codes", () => {
    expect(formatCurrency(7.5, "NOT_A_CODE")).toBe("$7.50");
  });

  it("respects zero and negative amounts", () => {
    expect(formatCurrency(0, "USD")).toBe("$0.00");
    expect(formatCurrency(-3.25, "EUR")).toBe("-€3.25");
  });
});

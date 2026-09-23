import { describe, it, expect } from "vitest";
import { formatReadout, formatNumber, formatPercent } from "./format";

describe("formatReadout", () => {
  it("formats positive signed numbers", () => {
    expect(formatReadout(12.5, "+.2f", "px")).toBe("+12.50 px");
  });

  it("formats negative signed numbers with unicode minus U+2212", () => {
    expect(formatReadout(-7.5, "+.2f", "px")).toBe("−7.50 px");
  });

  it("formats fixed precision numbers", () => {
    expect(formatReadout(0.852, ".2f")).toBe("0.85");
    expect(formatReadout(-3.1415, ".2f")).toBe("−3.14");
  });

  it("formats integers with d format", () => {
    expect(formatReadout(42, "d")).toBe("42");
    expect(formatReadout(-10, "d")).toBe("−10");
  });

  it("formats percentages with pct format", () => {
    expect(formatReadout(0.954, "pct")).toBe("95.4%");
  });

  it("handles null / undefined safely", () => {
    expect(formatReadout(null)).toBe("—");
    expect(formatReadout(undefined)).toBe("—");
  });

  it("handles string values", () => {
    expect(formatReadout("PASS", "", "")).toBe("PASS");
    expect(formatReadout("HIGH", "", "dB")).toBe("HIGH dB");
  });
});

describe("formatNumber", () => {
  it("formats positive and negative numbers with unicode minus", () => {
    expect(formatNumber(10.5)).toBe("10.50");
    expect(formatNumber(-10.5)).toBe("−10.50");
  });
});

describe("formatPercent", () => {
  it("formats decimal ratio to integer percent", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(1.0)).toBe("100%");
    expect(formatPercent(0.125)).toBe("13%");
  });
});

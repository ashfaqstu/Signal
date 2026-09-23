/**
 * Number and readout formatting utilities.
 * Uses U+2212 (−) for negative signs and tabular monospace numbers.
 */

export function formatReadout(
  value: number | string | null | undefined,
  fmt: string = "",
  unit: string = ""
): string {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "string") {
    return unit ? `${value} ${unit}` : value;
  }

  let formatted = "";

  if (fmt.startsWith("+")) {
    const precision = parseInt(fmt.slice(2, -1), 10) || 2;
    const sign = value >= 0 ? "+" : "−";
    formatted = `${sign}${Math.abs(value).toFixed(precision)}`;
  } else if (fmt.endsWith("f")) {
    const precision = parseInt(fmt.slice(1, -1), 10) || 2;
    const sign = value < 0 ? "−" : "";
    formatted = `${sign}${Math.abs(value).toFixed(precision)}`;
  } else if (fmt === "d") {
    const sign = value < 0 ? "−" : "";
    formatted = `${sign}${Math.abs(Math.round(value))}`;
  } else if (fmt === "pct") {
    formatted = `${(value * 100).toFixed(1)}%`;
  } else {
    // Default fallback
    const precision = Number.isInteger(value) ? 0 : 2;
    const sign = value < 0 ? "−" : "";
    formatted = `${sign}${Math.abs(value).toFixed(precision)}`;
  }

  return unit ? `${formatted} ${unit}` : formatted;
}

export function formatNumber(val: number, decimals: number = 2): string {
  const sign = val < 0 ? "−" : "";
  return `${sign}${Math.abs(val).toFixed(decimals)}`;
}

export function formatPercent(val: number): string {
  return `${Math.round(val * 100)}%`;
}

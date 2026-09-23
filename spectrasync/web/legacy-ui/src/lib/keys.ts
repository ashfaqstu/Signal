/**
 * Keyboard shortcut matcher.
 */

export function isShortcut(e: KeyboardEvent, shortcut: string): boolean {
  const parts = shortcut.toLowerCase().split("+");
  const key = parts[parts.length - 1];
  const needCtrl = parts.includes("ctrl") || parts.includes("cmd");
  const needAlt = parts.includes("alt");
  const needShift = parts.includes("shift");

  const hasCtrl = e.ctrlKey || e.metaKey;
  const hasAlt = e.altKey;
  const hasShift = e.shiftKey;

  if (needCtrl !== hasCtrl) return false;
  if (needAlt !== hasAlt) return false;
  if (needShift !== hasShift) return false;

  if (key === "0" && e.key === "0") return true;
  if (key === "1" && e.key === "1") return true;
  if (key === "=" && (e.key === "=" || e.key === "+")) return true;
  if (key === "-" && (e.key === "-" || e.key === "_")) return true;
  if (key === "enter" && e.key === "Enter") return true;
  if (key === "tab" && e.key === "Tab") return true;

  return e.key.toLowerCase() === key;
}

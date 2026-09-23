import React from "react";
import clsx from "clsx";
import { X } from "lucide-react";
import styles from "./Shell.module.css";

export interface ShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { key: "Alt+1 .. Alt+6", action: "Switch Workspace" },
  { key: "H", action: "Hand Tool (Pan)" },
  { key: "Z", action: "Zoom Tool (Click / Alt+Click)" },
  { key: "I", action: "Probe Tool (Pixel value)" },
  { key: "C", action: "Compare Split Tool" },
  { key: "Space + Drag", action: "Pan Canvas" },
  { key: "Wheel", action: "Zoom Canvas" },
  { key: "Ctrl + 0", action: "Fit to View" },
  { key: "Ctrl + 1", action: "Actual Size (100%)" },
  { key: "Ctrl + Enter", action: "Run Analysis" },
  { key: "Tab", action: "Toggle Panels" },
  { key: "J / K / L", action: "Backward / Pause / Forward" },
  { key: "← / →", action: "Step Frame" },
  { key: "Home / End", action: "First / Last Frame" },
  { key: "Ctrl + O", action: "Import Media" },
  { key: "Ctrl + E", action: "Export Current Layer" },
];

export const ShortcutsModal: React.FC<ShortcutsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={clsx(styles.modalCard, "popover-card")} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <span className={styles.modalTitle}>Keyboard Shortcuts</span>
          <button type="button" onClick={onClose} className={styles.modalCloseBtn}>
            <X size={16} />
          </button>
        </div>
        <div className={styles.shortcutsTableWrapper}>
          <table className={styles.shortcutsTable}>
            <tbody>
              {SHORTCUTS.map((s) => (
                <tr key={s.key}>
                  <td className={styles.shortcutKey}>
                    <kbd>{s.key}</kbd>
                  </td>
                  <td className={styles.shortcutAction}>{s.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import clsx from "clsx";
import styles from "./Shell.module.css";
import { WORKSPACES } from "../workspaces";
import { useUiStore } from "../state/ui";

export const WorkspaceTabs: React.FC = () => {
  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useUiStore((s) => s.setActiveWorkspace);

  return (
    <div className={styles.workspaceTabs}>
      {WORKSPACES.map((w) => {
        const isActive = w.id === activeWorkspace;
        const Icon = w.icon;
        return (
          <button
            key={w.id}
            type="button"
            className={clsx(
              styles.workspaceTab,
              isActive && styles.workspaceTabActive
            )}
            onClick={() => setActiveWorkspace(w.id)}
            title={`${w.label} (${w.shortcut})`}
          >
            <Icon size={14} className={styles.wsIcon} />
            <span>{w.label}</span>
          </button>
        );
      })}
    </div>
  );
};

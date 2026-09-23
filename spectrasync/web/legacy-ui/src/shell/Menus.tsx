import React, { useState, useRef, useEffect } from "react";
import clsx from "clsx";
import styles from "./Shell.module.css";
import { useUiStore } from "../state/ui";
import { useViewportStore } from "../state/viewport";
import { useParamsStore } from "../state/params";
import { getWorkspaceDef } from "../workspaces";

export interface MenusProps {
  onImportClick: () => void;
  onOpenShortcuts: () => void;
}

export const Menus: React.FC<MenusProps> = ({ onImportClick, onOpenShortcuts }) => {
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const activeWorkspace = useUiStore((s) => s.activeWorkspace);
  const setLayout = useUiStore((s) => s.setLayout);
  const theme = useUiStore((s) => s.theme);
  const setTheme = useUiStore((s) => s.setTheme);
  const togglePanelsHidden = useUiStore((s) => s.togglePanelsHidden);
  const setActiveRightTab = useUiStore((s) => s.setActiveRightTab);

  const fit = useViewportStore((s) => s.fit);
  const reset100 = useViewportStore((s) => s.reset100);
  const stepZoom = useViewportStore((s) => s.stepZoom);

  const resetParams = useParamsStore((s) => s.resetParams);
  const result = useParamsStore((s) => s.results[activeWorkspace]);

  const def = getWorkspaceDef(activeWorkspace);
  const isSequenceWorkspace = def.sequence !== "never";

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExportLayer = () => {
    if (!result) return;
    const activeLayer = result.layers[0]?.name || "output";
    window.location.href = `/api/runs/${result.runId}/export?layer=${encodeURIComponent(activeLayer)}&format=png`;
  };

  const handleExportSequence = () => {
    if (!result) return;
    window.location.href = `/api/runs/${result.runId}/export-sequence?format=mp4&fps=12`;
  };

  return (
    <div className={styles.menuBar} ref={menuRef}>
      {/* File Menu */}
      <div className={styles.menuWrapper}>
        <button
          type="button"
          className={clsx(styles.menuBtn, openMenu === "file" && styles.menuBtnActive)}
          onClick={() => setOpenMenu(openMenu === "file" ? null : "file")}
        >
          File
        </button>
        {openMenu === "file" && (
          <div className={clsx(styles.menuDropdown, "popover-card")}>
            <div
              className={styles.menuItem}
              onClick={() => {
                onImportClick();
                setOpenMenu(null);
              }}
            >
              <span>Import…</span>
              <kbd>Ctrl+O</kbd>
            </div>
            <div
              className={clsx(styles.menuItem, !result && styles.menuItemDisabled)}
              onClick={() => {
                if (result) {
                  handleExportLayer();
                  setOpenMenu(null);
                }
              }}
            >
              <span>Export Layer…</span>
              <kbd>Ctrl+E</kbd>
            </div>
            {isSequenceWorkspace && (
              <div
                className={clsx(styles.menuItem, !result && styles.menuItemDisabled)}
                onClick={() => {
                  if (result) {
                    handleExportSequence();
                    setOpenMenu(null);
                  }
                }}
              >
                <span>Export Sequence…</span>
                <kbd>Ctrl+Shift+E</kbd>
              </div>
            )}
            <div className={styles.menuDivider} />
            <div
              className={styles.menuItem}
              onClick={() => {
                resetParams(activeWorkspace as any);
                setOpenMenu(null);
              }}
            >
              <span>Reset Workspace</span>
            </div>
          </div>
        )}
      </div>

      {/* View Menu */}
      <div className={styles.menuWrapper}>
        <button
          type="button"
          className={clsx(styles.menuBtn, openMenu === "view" && styles.menuBtnActive)}
          onClick={() => setOpenMenu(openMenu === "view" ? null : "view")}
        >
          View
        </button>
        {openMenu === "view" && (
          <div className={clsx(styles.menuDropdown, "popover-card")}>
            <div
              className={styles.menuItem}
              onClick={() => {
                fit(window.innerWidth - 350, window.innerHeight - 150);
                setOpenMenu(null);
              }}
            >
              <span>Fit</span>
              <kbd>Ctrl+0</kbd>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                reset100(window.innerWidth - 350, window.innerHeight - 150);
                setOpenMenu(null);
              }}
            >
              <span>100 %</span>
              <kbd>Ctrl+1</kbd>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                stepZoom(1);
                setOpenMenu(null);
              }}
            >
              <span>Zoom In</span>
              <kbd>Ctrl+=</kbd>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                stepZoom(-1);
                setOpenMenu(null);
              }}
            >
              <span>Zoom Out</span>
              <kbd>Ctrl+-</kbd>
            </div>
            <div className={styles.menuDivider} />
            <div
              className={styles.menuItem}
              onClick={() => {
                setLayout("1up");
                setOpenMenu(null);
              }}
            >
              <span>1-Up</span>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setLayout("2up");
                setOpenMenu(null);
              }}
            >
              <span>2-Up</span>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setLayout("4up");
                setOpenMenu(null);
              }}
            >
              <span>4-Up</span>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setLayout("split");
                setOpenMenu(null);
              }}
            >
              <span>Split</span>
            </div>
            <div className={styles.menuDivider} />
            <div
              className={styles.menuItem}
              onClick={() => {
                setTheme("system");
                setOpenMenu(null);
              }}
            >
              <span>Theme: System</span>
              {theme === "system" && <span>✓</span>}
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setTheme("light");
                setOpenMenu(null);
              }}
            >
              <span>Theme: Light</span>
              {theme === "light" && <span>✓</span>}
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setTheme("dark");
                setOpenMenu(null);
              }}
            >
              <span>Theme: Dark</span>
              {theme === "dark" && <span>✓</span>}
            </div>
          </div>
        )}
      </div>

      {/* Window Menu */}
      <div className={styles.menuWrapper}>
        <button
          type="button"
          className={clsx(styles.menuBtn, openMenu === "window" && styles.menuBtnActive)}
          onClick={() => setOpenMenu(openMenu === "window" ? null : "window")}
        >
          Window
        </button>
        {openMenu === "window" && (
          <div className={clsx(styles.menuDropdown, "popover-card")}>
            <div
              className={styles.menuItem}
              onClick={() => {
                setActiveRightTab("layers");
                setOpenMenu(null);
              }}
            >
              <span>Layers</span>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setActiveRightTab("media");
                setOpenMenu(null);
              }}
            >
              <span>Media Bin</span>
            </div>
            <div
              className={styles.menuItem}
              onClick={() => {
                setActiveRightTab("graph");
                setOpenMenu(null);
              }}
            >
              <span>Graph & Tables</span>
            </div>
            <div className={styles.menuDivider} />
            <div
              className={styles.menuItem}
              onClick={() => {
                togglePanelsHidden();
                setOpenMenu(null);
              }}
            >
              <span>Toggle Panels</span>
              <kbd>Tab</kbd>
            </div>
          </div>
        )}
      </div>

      {/* Help Menu */}
      <div className={styles.menuWrapper}>
        <button
          type="button"
          className={clsx(styles.menuBtn, openMenu === "help" && styles.menuBtnActive)}
          onClick={() => setOpenMenu(openMenu === "help" ? null : "help")}
        >
          Help
        </button>
        {openMenu === "help" && (
          <div className={clsx(styles.menuDropdown, "popover-card")}>
            <div
              className={styles.menuItem}
              onClick={() => {
                onOpenShortcuts();
                setOpenMenu(null);
              }}
            >
              <span>Keyboard Shortcuts</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

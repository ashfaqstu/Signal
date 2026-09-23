import React from "react";
import styles from "./Shell.module.css";
import { Menus } from "./Menus";
import { WorkspaceTabs } from "./WorkspaceTabs";
import { ThemeToggle } from "./ThemeToggle";
import { Activity } from "lucide-react";

export interface AppBarProps {
  onImportClick: () => void;
  onOpenShortcuts: () => void;
}

export const AppBar: React.FC<AppBarProps> = ({ onImportClick, onOpenShortcuts }) => {
  return (
    <header className={styles.appBar}>
      <div className={styles.appBarLeft}>
        <div className={styles.brand}>
          <Activity size={16} className={styles.brandIcon} />
          <span className={styles.brandName}>SpectraSync</span>
        </div>
        <Menus onImportClick={onImportClick} onOpenShortcuts={onOpenShortcuts} />
      </div>

      <div className={styles.appBarCenter}>
        <WorkspaceTabs />
      </div>

      <div className={styles.appBarRight}>
        <ThemeToggle />
      </div>
    </header>
  );
};

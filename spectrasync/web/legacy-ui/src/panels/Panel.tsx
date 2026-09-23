import React, { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronRight } from "lucide-react";
import styles from "./Panels.module.css";

export interface PanelProps {
  title: string;
  defaultOpen?: boolean;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  collapsible?: boolean;
}

export const Panel: React.FC<PanelProps> = ({
  title,
  defaultOpen = true,
  actions,
  children,
  className,
  collapsible = true,
}) => {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={clsx(styles.panel, className)}>
      <div
        className={clsx(styles.panelHeader, collapsible && styles.clickable)}
        onClick={() => collapsible && setOpen(!open)}
      >
        <div className={styles.headerLeft}>
          {collapsible && (
            <span className={styles.chevron}>
              {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          )}
          <span className={styles.panelTitle}>{title}</span>
        </div>
        {actions && (
          <div className={styles.headerActions} onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
      </div>
      {open && <div className={styles.panelBody}>{children}</div>}
    </div>
  );
};

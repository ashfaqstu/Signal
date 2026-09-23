import React from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";

export interface BadgeProps {
  label: string;
  tone?: "default" | "ok" | "warn" | "bad" | "accent" | "muted";
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ label, tone = "default", className }) => {
  return (
    <span className={clsx(styles.badge, styles[`badge-${tone}`], className)}>
      {label}
    </span>
  );
};

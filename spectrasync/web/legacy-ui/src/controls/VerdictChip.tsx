import React from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";

export interface VerdictChipProps {
  verdict?: "locked" | "marginal" | "no lock" | string | null;
  className?: string;
}

export const VerdictChip: React.FC<VerdictChipProps> = ({ verdict, className }) => {
  if (!verdict) return null;

  let label = "LOCK";
  let tone = "ok";

  if (verdict === "marginal") {
    label = "WEAK";
    tone = "warn";
  } else if (verdict === "no lock" || verdict === "lost") {
    label = "LOST";
    tone = "bad";
  }

  return (
    <span className={clsx(styles.verdictChip, styles[`verdict-${tone}`], className)}>
      <span className={styles.verdictDot} />
      {label}
    </span>
  );
};

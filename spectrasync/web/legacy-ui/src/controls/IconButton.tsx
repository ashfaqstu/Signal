import React from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  active?: boolean;
  tooltip?: string;
  size?: "sm" | "md" | "tool";
}

export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  active = false,
  tooltip,
  size = "md",
  className,
  title,
  ...props
}) => {
  return (
    <button
      className={clsx(
        styles.iconButton,
        styles[`iconBtn-${size}`],
        active && styles.iconBtnActive,
        className
      )}
      title={tooltip || title}
      aria-label={tooltip || title}
      {...props}
    >
      {icon}
    </button>
  );
};

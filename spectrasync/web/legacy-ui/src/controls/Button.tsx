import React from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "default" | "ghost" | "accent";
  size?: "sm" | "md";
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "default",
  size = "md",
  icon,
  className,
  ...props
}) => {
  return (
    <button
      className={clsx(
        styles.button,
        styles[`btn-${variant}`],
        styles[`btn-${size}`],
        className
      )}
      {...props}
    >
      {icon && <span className={styles.btnIcon}>{icon}</span>}
      {children}
    </button>
  );
};

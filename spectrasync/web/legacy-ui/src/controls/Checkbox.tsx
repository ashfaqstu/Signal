import React from "react";
import clsx from "clsx";
import { Check } from "lucide-react";
import styles from "./Controls.module.css";

export interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  label,
  checked,
  onChange,
  disabled = false,
  className,
}) => {
  return (
    <label
      className={clsx(
        styles.checkboxLabel,
        disabled && styles.disabled,
        className
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className={styles.hiddenInput}
      />
      <div className={clsx(styles.checkboxBox, checked && styles.checkboxChecked)}>
        {checked && <Check size={12} strokeWidth={3} />}
      </div>
      <span className={styles.checkboxText}>{label}</span>
    </label>
  );
};

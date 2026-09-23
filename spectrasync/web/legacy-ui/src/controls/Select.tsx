import React from "react";
import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import styles from "./Controls.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  label?: string;
  options: SelectOption[] | string[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  value,
  onChange,
  disabled = false,
  className,
}) => {
  const normalizedOptions: SelectOption[] = options.map((opt) =>
    typeof opt === "string" ? { value: opt, label: opt } : opt
  );

  return (
    <div className={clsx(styles.selectWrapper, className)}>
      {label && <span className={styles.fieldLabel}>{label}</span>}
      <div className={styles.selectContainer}>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={clsx(styles.select, disabled && styles.disabled)}
        >
          {normalizedOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className={styles.selectChevron} />
      </div>
    </div>
  );
};

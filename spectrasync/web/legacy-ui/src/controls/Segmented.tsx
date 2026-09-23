import React from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";

export interface SegmentedOption {
  value: string;
  label: string;
}

export interface SegmentedProps {
  options: SegmentedOption[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export const Segmented: React.FC<SegmentedProps> = ({
  options,
  value,
  onChange,
  disabled = false,
  className,
}) => {
  return (
    <div className={clsx(styles.segmented, disabled && styles.disabled, className)}>
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            className={clsx(
              styles.segmentedItem,
              isSelected && styles.segmentedItemSelected
            )}
            onClick={() => !disabled && onChange(opt.value)}
            disabled={disabled}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};

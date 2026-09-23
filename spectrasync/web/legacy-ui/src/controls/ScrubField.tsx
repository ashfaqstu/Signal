import React, { useState, useRef, useEffect, useCallback } from "react";
import clsx from "clsx";
import styles from "./Controls.module.css";
import { formatNumber } from "../lib/format";

export interface ScrubFieldProps {
  label: string;
  value: number;
  defaultValue?: number;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  decimals?: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  className?: string;
}

export const ScrubField: React.FC<ScrubFieldProps> = ({
  label,
  value,
  defaultValue,
  min = -Infinity,
  max = Infinity,
  step = 1,
  unit = "",
  decimals,
  onChange,
  disabled = false,
  className,
}) => {
  const [editing, setEditing] = useState(false);
  const [textVal, setTextVal] = useState(String(value));
  const isDraggingRef = useRef(false);
  const startXRef = useRef(0);
  const startValRef = useRef(value);

  const numDecimals =
    decimals !== undefined
      ? decimals
      : step.toString().includes(".")
      ? step.toString().split(".")[1].length
      : 0;

  useEffect(() => {
    if (!editing) {
      setTextVal(value.toFixed(numDecimals));
    }
  }, [value, numDecimals, editing]);

  const clampValue = useCallback(
    (v: number) => {
      const clamped = Math.max(min, Math.min(max, v));
      // Round to precision
      const factor = Math.pow(10, numDecimals);
      return Math.round(clamped * factor) / factor;
    },
    [min, max, numDecimals]
  );

  const handlePointerDown = (e: React.PointerEvent<HTMLSpanElement>) => {
    if (disabled || editing) return;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    isDraggingRef.current = true;
    startXRef.current = e.clientX;
    startValRef.current = value;
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLSpanElement>) => {
    if (!isDraggingRef.current) return;
    const deltaX = e.clientX - startXRef.current;
    let multiplier = 1;
    if (e.shiftKey) multiplier = 10;
    if (e.altKey) multiplier = 0.1;

    const change = deltaX * step * multiplier;
    const newVal = clampValue(startValRef.current + change);
    onChange(newVal);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLSpanElement>) => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignore
      }
    }
  };

  const handleDoubleClick = () => {
    if (disabled) return;
    if (defaultValue !== undefined) {
      onChange(clampValue(defaultValue));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      commitText();
    } else if (e.key === "Escape") {
      setEditing(false);
      setTextVal(value.toFixed(numDecimals));
    } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      e.preventDefault();
      let mult = 1;
      if (e.shiftKey) mult = 10;
      if (e.altKey) mult = 0.1;
      const delta = (e.key === "ArrowUp" ? 1 : -1) * step * mult;
      const next = clampValue(value + delta);
      onChange(next);
      setTextVal(next.toFixed(numDecimals));
    }
  };

  const commitText = () => {
    setEditing(false);
    const parsed = parseFloat(textVal.replace("−", "-"));
    if (!isNaN(parsed)) {
      onChange(clampValue(parsed));
    } else {
      setTextVal(value.toFixed(numDecimals));
    }
  };

  return (
    <div className={clsx(styles.scrubWrapper, disabled && styles.disabled, className)}>
      <span
        className={styles.scrubLabel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onDoubleClick={handleDoubleClick}
        title="Drag horizontally to adjust · Double-click to reset"
      >
        {label}
      </span>
      <div className={styles.scrubFieldBox}>
        {editing ? (
          <input
            type="text"
            className={styles.scrubInput}
            value={textVal}
            onChange={(e) => setTextVal(e.target.value)}
            onBlur={commitText}
            onKeyDown={handleKeyDown}
            autoFocus
          />
        ) : (
          <span
            className={clsx(styles.scrubValue, "tabular-nums")}
            onClick={() => !disabled && setEditing(true)}
          >
            {formatNumber(value, numDecimals)}
            {unit && <span className={styles.fieldUnit}>{unit}</span>}
          </span>
        )}
      </div>
    </div>
  );
};

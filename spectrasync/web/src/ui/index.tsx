import { ChevronDown } from "lucide-react";
import {
  type ButtonHTMLAttributes,
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type { LucideIcon } from "lucide-react";
import s from "./ui.module.css";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

/* ---------- Button ---------- */

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "glass" | "white";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  iconOnly?: boolean;
};

export function Button({
  variant = "secondary",
  size = "md",
  icon: Icon,
  iconOnly,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cx(s.btn, s[variant], size !== "md" && s[size], iconOnly && s.iconOnly, className)}
      {...rest}
    >
      {Icon && <Icon size={size === "sm" ? 16 : 18} strokeWidth={2} />}
      {!iconOnly && children}
    </button>
  );
}

/* ---------- Slider ---------- */

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  digits?: number;
  /** Called once the user lets go, not on every pixel of drag. */
  onCommit: (v: number) => void;
}

export function Slider({ label, value, min, max, step, unit, digits = 0, onCommit }: SliderProps) {
  const [local, setLocal] = useState(value);
  const [text, setText] = useState(value.toFixed(digits));
  const dragging = useRef(false);

  useEffect(() => {
    if (!dragging.current) {
      setLocal(value);
      setText(value.toFixed(digits));
    }
  }, [value, digits]);

  const clamp = (v: number) => Math.min(max, Math.max(min, v));
  const commit = (v: number) => {
    dragging.current = false;
    const c = clamp(v);
    setLocal(c);
    setText(c.toFixed(digits));
    if (c !== value) onCommit(c);
  };
  const pct = ((local - min) / (max - min)) * 100;

  return (
    <div className={s.field}>
      <div className={s.fieldHead}>
        <span className={s.label}>{label}</span>
        <label className={s.valueBox}>
          <input
            inputMode="decimal"
            value={text}
            aria-label={label}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => commit(Number.isFinite(parseFloat(text)) ? parseFloat(text) : value)}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          />
          {unit && <span>{unit}</span>}
        </label>
      </div>
      <input
        type="range"
        className={s.range}
        style={{ ["--pct" as string]: `${pct}%` }}
        min={min}
        max={max}
        step={step}
        value={local}
        aria-label={label}
        onPointerDown={() => (dragging.current = true)}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          setLocal(v);
          setText(v.toFixed(digits));
        }}
        onPointerUp={(e) => commit(parseFloat((e.target as HTMLInputElement).value))}
        onKeyUp={(e) => commit(parseFloat((e.target as HTMLInputElement).value))}
      />
    </div>
  );
}

/* ---------- Chips ---------- */

interface Option<T> {
  value: T;
  label: string;
}

export function Chips<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label?: string;
  value: T;
  options: Option<T>[];
  onChange: (v: T) => void;
}) {
  return (
    <div className={s.field}>
      {label && <span className={s.label}>{label}</span>}
      <div className={s.chips} role="radiogroup" aria-label={label}>
        {options.map((o) => (
          <button
            key={String(o.value)}
            role="radio"
            aria-checked={o.value === value}
            className={cx(s.chip, o.value === value && s.chipOn)}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---------- Segmented (sliding thumb) ---------- */

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: (Option<T> & { icon?: LucideIcon })[];
  onChange: (v: T) => void;
  ariaLabel: string;
}) {
  const i = Math.max(0, options.findIndex((o) => o.value === value));
  return (
    <div className={s.seg} role="group" aria-label={ariaLabel}>
      <span
        className={s.segThumb}
        style={{ width: `calc((100% - 6px) / ${options.length})`, transform: `translateX(${i * 100}%)` }}
      />
      {options.map((o) => (
        <button
          key={o.value}
          className={s.segBtn}
          aria-pressed={o.value === value}
          aria-label={o.label || o.value}
          title={o.label ? undefined : o.value.charAt(0).toUpperCase() + o.value.slice(1)}
          onClick={() => onChange(o.value)}
        >
          {o.icon && <o.icon size={15} strokeWidth={2} />}
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ---------- Switch ---------- */

export function Switch({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      className={s.switchRow}
      role="switch"
      aria-checked={value}
      onClick={() => onChange(!value)}
    >
      <span className={s.label}>{label}</span>
      <span className={cx(s.switch, value && s.switchOn)} />
    </button>
  );
}

/* ---------- Select ---------- */

export function Select<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (v: T) => void;
}) {
  return (
    <div className={s.field}>
      <span className={s.label}>{label}</span>
      <div className={s.select}>
        <select value={value} aria-label={label} onChange={(e) => onChange(e.target.value as T)}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <ChevronDown size={16} />
      </div>
    </div>
  );
}

/* ---------- Menu ---------- */

export function Menu({
  trigger,
  children,
  align = "left",
}: {
  trigger: (open: boolean, toggle: () => void) => ReactNode;
  children: (close: () => void) => ReactNode;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={s.menuWrap} ref={ref}>
      {trigger(open, () => setOpen((o) => !o))}
      {open && (
        <div className={cx(s.menu, align === "right" && s.menuRight)} role="menu">
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

export function MenuItem({
  icon,
  label,
  sub,
  onClick,
}: {
  icon?: ReactNode;
  label: string;
  sub?: string;
  onClick: () => void;
}) {
  return (
    <button className={s.menuItem} role="menuitem" onClick={onClick}>
      {icon}
      <span>
        {label}
        {sub && <span className={s.menuItemSub}>{sub}</span>}
      </span>
    </button>
  );
}

/* ---------- ToolBadge: gradient tile with the tool icon ---------- */

export function ToolBadge({
  icon: Icon,
  gradient,
  size = 40,
  radius = 12,
}: {
  icon: LucideIcon;
  gradient: string;
  size?: number;
  radius?: number;
}) {
  return (
    <span className={s.badge} style={{ width: size, height: size, borderRadius: radius, background: gradient }}>
      <Icon size={Math.round(size * 0.5)} strokeWidth={2} />
    </span>
  );
}

/* ---------- small pieces ---------- */

export function Spinner() {
  return <span className={s.spinner} aria-hidden />;
}

export function StatusPill({ tone, children }: { tone: "ok" | "warn" | "bad" | "muted"; children: ReactNode }) {
  return (
    <span className={cx(s.pill, s[`pill${tone}`])}>
      <span className={s.dot} />
      {children}
    </span>
  );
}

export { cx };

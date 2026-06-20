import { Minus, Plus } from "lucide-react";
import type { InputHTMLAttributes, ReactNode } from "react";

export function FieldShell({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="eyebrow mb-1.5 flex items-center justify-between">
        <span>{label}</span>
        {hint}
      </span>
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink placeholder:text-faint outline-none transition-colors focus:border-cobalt";

export function TextField(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function inputClassName() {
  return inputClass;
}

// A typed numeric field with − / + steppers. Precise (you can type a value) and
// discrete, unlike a slider where the exact number is hard to land on.
export function NumberStepper({
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
}: {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
}) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n));
  const stepBtn =
    "grid w-9 shrink-0 place-items-center text-muted transition-colors hover:text-cobalt disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:text-muted";

  return (
    <div className="flex items-stretch overflow-hidden rounded-lg border border-line bg-surface transition-colors focus-within:border-cobalt">
      <button
        type="button"
        aria-label="Decrease"
        disabled={value <= min}
        onClick={() => onChange(clamp(value - step))}
        className={stepBtn}
      >
        <Minus className="size-3.5" />
      </button>
      <div className="flex flex-1 items-baseline justify-center gap-1 border-x border-line py-2">
        <input
          type="number"
          inputMode="numeric"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) =>
            onChange(e.target.value === "" ? min : clamp(Number(e.target.value)))
          }
          className="data w-10 bg-transparent text-right text-sm font-bold text-ink outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        {suffix && <span className="text-xs text-faint">{suffix}</span>}
      </div>
      <button
        type="button"
        aria-label="Increase"
        disabled={value >= max}
        onClick={() => onChange(clamp(value + step))}
        className={stepBtn}
      >
        <Plus className="size-3.5" />
      </button>
    </div>
  );
}

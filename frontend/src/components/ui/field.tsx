import { useId, type InputHTMLAttributes, type ReactNode } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  galat?: string | null;
  bantuan?: ReactNode;
}

/** Label + input + pesan galat, terhubung lewat aria agar terbaca pembaca layar. */
export function Field({ label, galat, bantuan, className = "", id, ...rest }: Props) {
  const otomatis = useId();
  const inputId = id ?? otomatis;
  const pesanId = `${inputId}-pesan`;
  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-stone-700">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={galat ? true : undefined}
        aria-describedby={galat || bantuan ? pesanId : undefined}
        {...rest}
        className={`block min-h-10 w-full rounded-lg border bg-white px-3 text-sm text-stone-900 placeholder:text-stone-400 ${
          galat ? "border-red-500" : "border-stone-300"
        } ${className}`}
      />
      {(galat || bantuan) && (
        <p id={pesanId} className={`text-xs ${galat ? "text-red-600" : "text-stone-500"}`}>
          {galat ?? bantuan}
        </p>
      )}
    </div>
  );
}

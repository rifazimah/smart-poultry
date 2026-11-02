import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

type Varian = "utama" | "sekunder" | "ghost" | "bahaya";

const gaya: Record<Varian, string> = {
  utama: "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-brand-700/50",
  sekunder: "border border-stone-300 bg-white text-stone-800 hover:bg-stone-100 disabled:text-stone-400",
  ghost: "text-stone-700 hover:bg-stone-200/60 disabled:text-stone-400",
  bahaya: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-600/50",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  varian?: Varian;
  memuat?: boolean;
}

/** Tombol dasar; target sentuh min. 40px agar nyaman di ponsel. */
export function Button({ varian = "utama", memuat = false, className = "", disabled, children, ...rest }: Props) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || memuat}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${gaya[varian]} ${className}`}
    >
      {memuat && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

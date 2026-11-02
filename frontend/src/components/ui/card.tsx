import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={`rounded-xl border border-stone-200 bg-white p-4 shadow-sm ${className}`} />;
}

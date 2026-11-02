import type { ReactNode } from "react";

export type NadaBadge = "netral" | "baik" | "peringatan" | "bahaya";

const gaya: Record<NadaBadge, string> = {
  netral: "bg-stone-100 text-stone-700",
  baik: "bg-brand-100 text-brand-800",
  peringatan: "bg-accent-100 text-accent-700",
  bahaya: "bg-red-100 text-red-700",
};

export function Badge({ nada = "netral", children }: { nada?: NadaBadge; children: ReactNode }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${gaya[nada]}`}>{children}</span>;
}

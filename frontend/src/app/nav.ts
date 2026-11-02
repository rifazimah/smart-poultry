import { Bell, LayoutDashboard, type LucideIcon } from "lucide-react";
import type { Peran } from "../auth/auth-context";

export interface ItemNav {
  ke: string;
  label: string;
  ikon: LucideIcon;
  /** Peran yang melihat menu ini. Otorisasi sebenarnya tetap di server. */
  peran: Peran[];
}

// Hanya halaman yang sudah ada yang didaftarkan di sini (tidak ada tautan mati). Tahap berikutnya menambah item.
export const MENU: ItemNav[] = [
  { ke: "/", label: "Dashboard", ikon: LayoutDashboard, peran: ["PEMILIK", "PEKERJA"] },
  { ke: "/notifikasi", label: "Notifikasi", ikon: Bell, peran: ["PEMILIK", "PEKERJA"] },
];

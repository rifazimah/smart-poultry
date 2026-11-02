import { createContext, useContext } from "react";
import type { Skema } from "../api/client";

export type Pengguna = Skema["UserPublic"];
export type Peran = Skema["PeranUser"];

export type StatusAuth = "memuat" | "masuk" | "keluar";

export interface AuthContextValue {
  pengguna: Pengguna | null;
  status: StatusAuth;
  /** Melempar ApiError bila gagal (kredensial salah, user nonaktif, terlalu banyak percobaan, ...). */
  masuk: (email: string, kataSandi: string) => Promise<void>;
  keluar: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth harus dipakai di dalam <AuthProvider>");
  return ctx;
}

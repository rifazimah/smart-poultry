import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Spinner } from "../components/ui/spinner";
import { useAuth, type Peran } from "./auth-context";

/**
 * Menjaga halaman: belum masuk -> /masuk; peran tidak sesuai -> beranda.
 * Ini hanya merapikan tampilan; otorisasi sebenarnya tetap dijalankan server (403/404).
 */
export function ProtectedRoute({ children, peran }: { children: ReactNode; peran?: Peran[] }) {
  const { status, pengguna } = useAuth();
  const lokasi = useLocation();

  if (status === "memuat") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Memuat sesi..." />
      </div>
    );
  }
  if (status === "keluar" || !pengguna) {
    return <Navigate to="/masuk" replace state={{ dari: lokasi.pathname }} />;
  }
  if (peran && !peran.includes(pengguna.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

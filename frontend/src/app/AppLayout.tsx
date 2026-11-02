import { Bell, LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/auth-context";
import { Button } from "../components/ui/button";
import { Dialog } from "../components/ui/dialog";
import { useJumlahNotifikasiBelumDibaca } from "../features/notifikasi/useNotifikasi";
import { MENU } from "./nav";

function DaftarMenu({ saatPilih }: { saatPilih?: () => void }) {
  const { pengguna } = useAuth();
  const item = MENU.filter((m) => pengguna && m.peran.includes(pengguna.role));
  return (
    <nav aria-label="Menu utama" className="flex flex-col gap-1">
      {item.map(({ ke, label, ikon: Ikon }) => (
        <NavLink
          key={ke}
          to={ke}
          end={ke === "/"}
          onClick={saatPilih}
          className={({ isActive }) =>
            `flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium ${
              isActive ? "bg-brand-100 text-brand-800" : "text-stone-700 hover:bg-stone-100"
            }`
          }
        >
          <Ikon className="h-5 w-5" aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { pengguna, keluar } = useAuth();
  const [laciTerbuka, setLaciTerbuka] = useState(false);
  const { data: belumDibaca } = useJumlahNotifikasiBelumDibaca();

  return (
    <div className="min-h-screen">
      {/* Sidebar desktop */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-stone-200 bg-white p-4 md:flex">
        <p className="mb-6 px-3 text-lg font-bold text-brand-800">Smart Poultry</p>
        <DaftarMenu />
      </aside>

      {/* Laci menu di ponsel */}
      <Dialog buka={laciTerbuka} saatBerubah={setLaciTerbuka} judul="Menu" posisi="kiri">
        <DaftarMenu saatPilih={() => setLaciTerbuka(false)} />
      </Dialog>

      <div className="md:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-stone-200 bg-white/95 px-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md p-2 text-stone-700 hover:bg-stone-100 md:hidden"
              onClick={() => setLaciTerbuka(true)}
              aria-label="Buka menu"
            >
              <Menu className="h-6 w-6" aria-hidden="true" />
            </button>
            <span className="font-bold text-brand-800 md:hidden">Smart Poultry</span>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <span
              className="relative p-2 text-stone-600"
              aria-label={`Notifikasi belum dibaca: ${belumDibaca ?? 0}`}
              role="img"
            >
              <Bell className="h-5 w-5" aria-hidden="true" />
              {!!belumDibaca && (
                <span className="absolute top-0 right-0 min-w-5 rounded-full bg-accent-500 px-1 text-center text-xs font-bold text-stone-900">
                  {belumDibaca > 99 ? "99+" : belumDibaca}
                </span>
              )}
            </span>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-stone-900">{pengguna?.nama}</p>
              <p className="text-xs text-stone-500">{pengguna?.role === "PEMILIK" ? "Pemilik" : "Pekerja"}</p>
            </div>
            <Button varian="ghost" onClick={keluar} aria-label="Keluar">
              <LogOut className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Keluar</span>
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-6xl p-3 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

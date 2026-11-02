import type { FormEvent, ReactNode } from "react";
import { pesanGalat } from "../../api/errors";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { useToast } from "../../components/ui/toast";

/** Dialog konfirmasi hapus; galat dari server (mis. 409 masih dipakai) ditampilkan di dalam dialog. */
export function KonfirmasiHapus({
  nama,
  saatTutup,
  saatHapus,
  memuat,
  galat,
}: {
  nama: string | null;
  saatTutup: () => void;
  saatHapus: () => void;
  memuat: boolean;
  galat: unknown;
}) {
  return (
    <Dialog
      buka={nama !== null}
      saatBerubah={(b) => !b && saatTutup()}
      judul="Hapus data?"
      deskripsi={`"${nama ?? ""}" akan dihapus. Data yang masih dipakai tidak dapat dihapus.`}
    >
      {galat != null && (
        <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {pesanGalat(galat)}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button varian="sekunder" onClick={saatTutup}>
          Batal
        </Button>
        <Button varian="bahaya" memuat={memuat} onClick={saatHapus}>
          Hapus
        </Button>
      </div>
    </Dialog>
  );
}

/** Dialog berisi formulir; menutup sendiri saat simpan berhasil dan menampilkan toast. */
export function FormDialog({
  judul,
  buka,
  saatTutup,
  saatKirim,
  memuat,
  galat,
  children,
}: {
  judul: string;
  buka: boolean;
  saatTutup: () => void;
  saatKirim: () => void;
  memuat: boolean;
  galat: unknown;
  children: ReactNode;
}) {
  const kirim = (e: FormEvent) => {
    e.preventDefault();
    saatKirim();
  };
  return (
    <Dialog buka={buka} saatBerubah={(b) => !b && saatTutup()} judul={judul}>
      <form onSubmit={kirim} className="space-y-3">
        {children}
        {galat != null && (
          <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
            {typeof galat === "string" ? galat : pesanGalat(galat)}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button varian="sekunder" onClick={saatTutup}>
            Batal
          </Button>
          <Button type="submit" memuat={memuat}>
            Simpan
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export { useToast };

/** Teks input -> angka; kosong = null. NaN dikembalikan sebagai undefined agar pemanggil dapat menolak. */
export function keAngka(teks: string): number | null | undefined {
  if (teks.trim() === "") return null;
  const n = Number(teks.replace(",", "."));
  return Number.isFinite(n) ? n : undefined;
}

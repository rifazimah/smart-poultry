import { useState } from "react";
import { pesanGalat } from "../../api/errors";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { ErrorState } from "../../components/ui/states";
import { formatBerat, formatWaktu, kgKeGram } from "../../lib/format";
import { FormDialog, useToast } from "../master-data/bersama";
import { useIsiUlang, useKoreksiStok, useRiwayatStok } from "./aksi";
import type { Stok } from "./useDetailKandang";

const LABEL_JENIS: Record<string, string> = {
  ISI_ULANG: "Isi ulang",
  KOREKSI_MANUAL: "Koreksi",
  PENGELUARAN: "Pengeluaran",
};

function Riwayat({ wadahId }: { wadahId: string }) {
  const { data, isPending, isError, error, refetch } = useRiwayatStok(wadahId);
  if (isPending) return <Spinner label="Memuat riwayat..." />;
  if (isError) return <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />;
  if (data.length === 0) return <p className="text-sm text-stone-500">Belum ada transaksi.</p>;
  return (
    <ul className="max-h-80 divide-y divide-stone-100 overflow-y-auto text-sm">
      {data.map((t) => (
        <li key={t.id} className="flex items-start justify-between gap-3 py-2">
          <span>
            <Badge>{LABEL_JENIS[t.jenis] ?? t.jenis}</Badge>
            {t.alasan && <span className="ml-2 text-stone-500">{t.alasan}</span>}
          </span>
          <span className="shrink-0 text-right">
            <span className="block font-medium text-stone-800">{formatBerat(t.jumlah)}</span>
            <span className="text-xs text-stone-500">{formatWaktu(t.dibuat_pada)}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Isi ulang, koreksi, dan riwayat stok satu wadah. Pemilik dan Pekerja yang ditugaskan boleh. Input dalam kg, dikirim dalam gram. */
export function AksiStok({ stok }: { stok: Stok }) {
  const { tampilkan } = useToast();
  const isi = useIsiUlang();
  const koreksi = useKoreksiStok();
  const [mode, setMode] = useState<"isi" | "koreksi" | "riwayat" | null>(null);
  const [kg, setKg] = useState("");
  const [alasan, setAlasan] = useState("");
  const [galatLokal, setGalatLokal] = useState<string | null>(null);
  const nama = stok.nama_bahan ?? "wadah";

  const buka = (m: "isi" | "koreksi" | "riwayat") => {
    setKg("");
    setAlasan("");
    setGalatLokal(null);
    isi.reset();
    koreksi.reset();
    setMode(m);
  };
  const tutup = () => setMode(null);

  const kirimIsi = () => {
    const gram = kgKeGram(kg);
    if (gram === undefined || gram <= 0) return setGalatLokal("Jumlah harus berupa angka lebih dari nol.");
    setGalatLokal(null);
    isi.mutate(
      { wadahId: stok.wadah_id, gram },
      {
        onSuccess: () => {
          tutup();
          tampilkan("Stok diisi ulang", { tipe: "sukses" });
        },
      },
    );
  };

  const kirimKoreksi = () => {
    const gram = kgKeGram(kg);
    if (gram === undefined || gram < 0) return setGalatLokal("Jumlah baru harus berupa angka nol atau lebih.");
    if (!alasan.trim()) return setGalatLokal("Alasan koreksi wajib diisi.");
    setGalatLokal(null);
    koreksi.mutate(
      { wadahId: stok.wadah_id, gramBaru: gram, alasan: alasan.trim() },
      {
        onSuccess: () => {
          tutup();
          tampilkan("Stok dikoreksi", { tipe: "sukses" });
        },
      },
    );
  };

  return (
    <div className="flex flex-wrap gap-1">
      <Button varian="sekunder" aria-label={`Isi ulang ${nama}`} onClick={() => buka("isi")}>
        Isi ulang
      </Button>
      <Button varian="ghost" aria-label={`Koreksi ${nama}`} onClick={() => buka("koreksi")}>
        Koreksi
      </Button>
      <Button varian="ghost" aria-label={`Riwayat ${nama}`} onClick={() => buka("riwayat")}>
        Riwayat
      </Button>

      <FormDialog
        judul={`Isi ulang: ${nama}`}
        buka={mode === "isi"}
        saatTutup={tutup}
        memuat={isi.isPending}
        galat={galatLokal ?? isi.error}
        saatKirim={kirimIsi}
      >
        <Field
          label="Jumlah ditambahkan (kg)"
          inputMode="decimal"
          value={kg}
          onChange={(e) => setKg(e.target.value)}
          required
          bantuan={`Stok sekarang ${formatBerat(stok.jumlah_estimasi)}.`}
        />
      </FormDialog>

      <FormDialog
        judul={`Koreksi stok: ${nama}`}
        buka={mode === "koreksi"}
        saatTutup={tutup}
        memuat={koreksi.isPending}
        galat={galatLokal ?? koreksi.error}
        saatKirim={kirimKoreksi}
      >
        <Field
          label="Jumlah sebenarnya (kg)"
          inputMode="decimal"
          value={kg}
          onChange={(e) => setKg(e.target.value)}
          required
          bantuan={`Menggantikan stok sekarang (${formatBerat(stok.jumlah_estimasi)}).`}
        />
        <Field label="Alasan" value={alasan} onChange={(e) => setAlasan(e.target.value)} required />
      </FormDialog>

      <Dialog buka={mode === "riwayat"} saatBerubah={(b) => !b && tutup()} judul={`Riwayat stok: ${nama}`}>
        {mode === "riwayat" && <Riwayat wadahId={stok.wadah_id} />}
      </Dialog>
    </div>
  );
}

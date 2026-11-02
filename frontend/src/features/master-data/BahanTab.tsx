import { useState } from "react";
import { pesanGalat } from "../../api/errors";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { formatAngka, formatRupiah } from "../../lib/format";
import { FormDialog, KonfirmasiHapus, keAngka, useToast } from "./bersama";
import {
  useDaftarBahan,
  useDaftarNutrisi,
  useHapusBahan,
  useKandunganBahan,
  useSimpanBahan,
  useSimpanKandungan,
  type Bahan,
} from "./hooks";

type StatusBahan = Bahan["status_sistem"];
const LABEL_STATUS: Record<StatusBahan, string> = { DI_DALAM_SISTEM: "Di dalam sistem", DI_LUAR_SISTEM: "Di luar sistem" };

function FormKandungan({ bahan, saatTutup }: { bahan: Bahan; saatTutup: () => void }) {
  const { tampilkan } = useToast();
  const nutrisi = useDaftarNutrisi();
  const kandungan = useKandunganBahan(bahan.id);
  const simpan = useSimpanKandungan(bahan.id);
  const [nilai, setNilai] = useState<Record<string, string>>({});
  const [galatLokal, setGalatLokal] = useState<string | null>(null);

  const siap = nutrisi.data && kandungan.data;
  const tampil = (nutrisiId: string) => {
    if (nilai[nutrisiId] !== undefined) return nilai[nutrisiId];
    const ada = kandungan.data?.find((k) => k.nutrisi_id === nutrisiId);
    return ada ? String(ada.nilai_per_kg) : "";
  };

  const kirim = () => {
    const baris: { nutrisi_id: string; nilai_per_kg: number }[] = [];
    for (const n of nutrisi.data ?? []) {
      const angka = keAngka(tampil(n.id));
      if (angka === undefined || (angka !== null && angka < 0)) {
        setGalatLokal(`Nilai ${n.nama} harus berupa angka nol atau lebih.`);
        return;
      }
      if (angka !== null) baris.push({ nutrisi_id: n.id, nilai_per_kg: angka });
    }
    setGalatLokal(null);
    simpan.mutate(baris, {
      onSuccess: () => {
        tampilkan("Kandungan nutrisi disimpan", { tipe: "sukses" });
        saatTutup();
      },
    });
  };

  return (
    <div className="space-y-3">
      {!siap && !nutrisi.isError && !kandungan.isError && <Spinner label="Memuat kandungan..." />}
      {(nutrisi.isError || kandungan.isError) && <ErrorState pesan={pesanGalat(nutrisi.error ?? kandungan.error)} />}
      {siap && nutrisi.data.length === 0 && <p className="text-sm text-stone-500">Tambahkan nutrisi terlebih dahulu.</p>}
      {siap && nutrisi.data.length > 0 && (
        <ul className="max-h-80 space-y-2 overflow-y-auto">
          {nutrisi.data.map((n) => (
            <li key={n.id} className="flex items-center justify-between gap-3">
              <label htmlFor={`k-${n.id}`} className="text-sm text-stone-800">
                {n.nama} <span className="text-stone-500">({n.satuan}/kg)</span>
              </label>
              <input
                id={`k-${n.id}`}
                inputMode="decimal"
                value={tampil(n.id)}
                onChange={(e) => setNilai((s) => ({ ...s, [n.id]: e.target.value }))}
                className="min-h-10 w-28 rounded-lg border border-stone-300 px-2 text-right text-sm"
              />
            </li>
          ))}
        </ul>
      )}
      {galatLokal && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{galatLokal}</p>}
      {simpan.isError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{pesanGalat(simpan.error)}</p>}
      <div className="flex justify-end gap-2">
        <Button varian="sekunder" onClick={saatTutup}>
          Batal
        </Button>
        <Button disabled={!siap} memuat={simpan.isPending} onClick={kirim}>
          Simpan kandungan
        </Button>
      </div>
    </div>
  );
}

export function BahanTab() {
  const { tampilkan } = useToast();
  const daftar = useDaftarBahan();
  const simpan = useSimpanBahan();
  const hapus = useHapusBahan();
  const [form, setForm] = useState<Bahan | "baru" | null>(null);
  const [nama, setNama] = useState("");
  const [harga, setHarga] = useState("");
  const [maks, setMaks] = useState("");
  const [status, setStatus] = useState<StatusBahan>("DI_DALAM_SISTEM");
  const [galatLokal, setGalatLokal] = useState<string | null>(null);
  const [akanHapus, setAkanHapus] = useState<Bahan | null>(null);
  const [kandungan, setKandungan] = useState<Bahan | null>(null);

  const bukaForm = (b: Bahan | "baru") => {
    setNama(b === "baru" ? "" : b.nama);
    setHarga(b === "baru" || b.harga == null ? "" : String(b.harga));
    setMaks(b === "baru" || b.batas_maksimum == null ? "" : String(b.batas_maksimum));
    setStatus(b === "baru" ? "DI_DALAM_SISTEM" : b.status_sistem);
    setGalatLokal(null);
    simpan.reset();
    setForm(b);
  };

  const kirim = () => {
    const h = keAngka(harga);
    const m = keAngka(maks);
    if (h === undefined || (h !== null && h < 0)) return setGalatLokal("Harga harus berupa angka nol atau lebih.");
    if (m === undefined || (m !== null && (m < 0 || m > 1))) return setGalatLokal("Batas maksimum berupa pecahan 0 sampai 1 (mis. 0,4 untuk 40%).");
    setGalatLokal(null);
    simpan.mutate(
      {
        id: form && form !== "baru" ? form.id : undefined,
        data: { nama: nama.trim(), harga: h, batas_maksimum: m, status_sistem: status },
      },
      {
        onSuccess: () => {
          setForm(null);
          tampilkan("Bahan pakan disimpan", { tipe: "sukses" });
        },
      },
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-stone-500">Bahan baku pakan beserta harga per kg dan kandungan nutrisinya.</p>
        <Button onClick={() => bukaForm("baru")}>Tambah bahan</Button>
      </div>
      {daftar.isPending && <Spinner label="Memuat bahan pakan..." />}
      {daftar.isError && <ErrorState pesan={pesanGalat(daftar.error)} ulangi={() => void daftar.refetch()} />}
      {daftar.data && daftar.data.length === 0 && <EmptyState judul="Belum ada bahan pakan" />}
      {daftar.data && daftar.data.length > 0 && (
        <ul className="space-y-2">
          {daftar.data.map((b) => (
            <li key={b.id}>
              <Card className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-stone-900">{b.nama}</p>
                  <p className="text-sm text-stone-500">
                    {formatRupiah(b.harga)}/kg · maks {b.batas_maksimum == null ? "tanpa batas" : `${formatAngka(b.batas_maksimum * 100)}%`}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge nada={b.status_sistem === "DI_DALAM_SISTEM" ? "baik" : "netral"}>{LABEL_STATUS[b.status_sistem]}</Badge>
                  <Button varian="sekunder" onClick={() => setKandungan(b)} aria-label={`Kandungan ${b.nama}`}>
                    Kandungan
                  </Button>
                  <Button varian="sekunder" onClick={() => bukaForm(b)} aria-label={`Ubah ${b.nama}`}>
                    Ubah
                  </Button>
                  <Button varian="ghost" onClick={() => { hapus.reset(); setAkanHapus(b); }} aria-label={`Hapus ${b.nama}`}>
                    Hapus
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <FormDialog
        judul={form === "baru" ? "Tambah bahan pakan" : "Ubah bahan pakan"}
        buka={form !== null}
        saatTutup={() => setForm(null)}
        memuat={simpan.isPending}
        galat={galatLokal ?? simpan.error}
        saatKirim={kirim}
      >
        <Field label="Nama" value={nama} onChange={(e) => setNama(e.target.value)} required />
        <Field label="Harga per kg (Rp)" inputMode="decimal" value={harga} onChange={(e) => setHarga(e.target.value)} />
        <Field
          label="Batas maksimum dalam campuran"
          inputMode="decimal"
          value={maks}
          onChange={(e) => setMaks(e.target.value)}
          bantuan="Pecahan 0 sampai 1, mis. 0,4 untuk 40%. Kosong = tanpa batas."
        />
        <div className="space-y-1">
          <label htmlFor="status-bahan" className="block text-sm font-medium text-stone-700">
            Status
          </label>
          <select
            id="status-bahan"
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusBahan)}
            className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm"
          >
            {(Object.keys(LABEL_STATUS) as StatusBahan[]).map((s) => (
              <option key={s} value={s}>
                {LABEL_STATUS[s]}
              </option>
            ))}
          </select>
        </div>
      </FormDialog>

      <KonfirmasiHapus
        nama={akanHapus?.nama ?? null}
        saatTutup={() => setAkanHapus(null)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          akanHapus &&
          hapus.mutate(akanHapus.id, {
            onSuccess: () => {
              setAkanHapus(null);
              tampilkan("Bahan pakan dihapus", { tipe: "sukses" });
            },
          })
        }
      />

      {kandungan && (
        <KandunganDialog bahan={kandungan} saatTutup={() => setKandungan(null)} />
      )}
    </div>
  );
}


function KandunganDialog({ bahan, saatTutup }: { bahan: Bahan; saatTutup: () => void }) {
  return (
    <Dialog buka saatBerubah={(b) => !b && saatTutup()} judul={`Kandungan nutrisi: ${bahan.nama}`} deskripsi="Nilai per kg bahan. Kosongkan bila tidak ada.">
      <FormKandungan bahan={bahan} saatTutup={saatTutup} />
    </Dialog>
  );
}

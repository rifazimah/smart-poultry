import { useState } from "react";
import { pesanGalat } from "../../api/errors";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { FormDialog, KonfirmasiHapus, useToast } from "./bersama";
import { useDaftarNutrisi, useHapusNutrisi, useSimpanNutrisi, type Nutrisi, type TipeBatas } from "./hooks";

export const LABEL_BATAS: Record<TipeBatas, string> = {
  MINIMUM: "Minimum",
  MAKSIMUM: "Maksimum",
  MIN_MAKS: "Minimum dan maksimum",
};

export function NutrisiTab() {
  const { tampilkan } = useToast();
  const daftar = useDaftarNutrisi();
  const simpan = useSimpanNutrisi();
  const hapus = useHapusNutrisi();
  const [form, setForm] = useState<Nutrisi | "baru" | null>(null);
  const [nama, setNama] = useState("");
  const [satuan, setSatuan] = useState("");
  const [tipe, setTipe] = useState<TipeBatas>("MIN_MAKS");
  const [akanHapus, setAkanHapus] = useState<Nutrisi | null>(null);

  const bukaForm = (n: Nutrisi | "baru") => {
    setNama(n === "baru" ? "" : n.nama);
    setSatuan(n === "baru" ? "" : n.satuan);
    setTipe(n === "baru" ? "MIN_MAKS" : n.tipe_batas);
    simpan.reset();
    setForm(n);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-stone-500">Zat gizi yang dihitung pada formulasi (protein, energi, dst.).</p>
        <Button onClick={() => bukaForm("baru")}>Tambah nutrisi</Button>
      </div>
      {daftar.isPending && <Spinner label="Memuat nutrisi..." />}
      {daftar.isError && <ErrorState pesan={pesanGalat(daftar.error)} ulangi={() => void daftar.refetch()} />}
      {daftar.data && daftar.data.length === 0 && <EmptyState judul="Belum ada nutrisi" />}
      {daftar.data && daftar.data.length > 0 && (
        <ul className="space-y-2">
          {daftar.data.map((n) => (
            <li key={n.id}>
              <Card className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-stone-900">{n.nama}</p>
                  <p className="text-sm text-stone-500">Satuan: {n.satuan}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge>{LABEL_BATAS[n.tipe_batas]}</Badge>
                  <Button varian="sekunder" onClick={() => bukaForm(n)} aria-label={`Ubah ${n.nama}`}>
                    Ubah
                  </Button>
                  <Button varian="ghost" onClick={() => { hapus.reset(); setAkanHapus(n); }} aria-label={`Hapus ${n.nama}`}>
                    Hapus
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <FormDialog
        judul={form === "baru" ? "Tambah nutrisi" : "Ubah nutrisi"}
        buka={form !== null}
        saatTutup={() => setForm(null)}
        memuat={simpan.isPending}
        galat={simpan.error}
        saatKirim={() =>
          simpan.mutate(
            { id: form && form !== "baru" ? form.id : undefined, data: { nama: nama.trim(), satuan: satuan.trim(), tipe_batas: tipe } },
            {
              onSuccess: () => {
                setForm(null);
                tampilkan("Nutrisi disimpan", { tipe: "sukses" });
              },
            },
          )
        }
      >
        <Field label="Nama" value={nama} onChange={(e) => setNama(e.target.value)} required />
        <Field label="Satuan" value={satuan} onChange={(e) => setSatuan(e.target.value)} required placeholder="%, kkal/kg, ..." />
        <div className="space-y-1">
          <label htmlFor="tipe-batas" className="block text-sm font-medium text-stone-700">
            Jenis batas
          </label>
          <select
            id="tipe-batas"
            value={tipe}
            onChange={(e) => setTipe(e.target.value as TipeBatas)}
            className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm"
          >
            {(Object.keys(LABEL_BATAS) as TipeBatas[]).map((t) => (
              <option key={t} value={t}>
                {LABEL_BATAS[t]}
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
              tampilkan("Nutrisi dihapus", { tipe: "sukses" });
            },
          })
        }
      />
    </div>
  );
}

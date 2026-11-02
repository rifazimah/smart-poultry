import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, pesanGalat } from "../../api/errors";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { FormDialog, KonfirmasiHapus, keAngka, useToast } from "./bersama";
import {
  useDaftarFase,
  useDaftarNutrisi,
  useHapusFase,
  useJenisAyam,
  useKebutuhanFase,
  useSimpanFase,
  useSimpanKebutuhan,
  useSimpanStandar,
  useStandarFase,
  type Fase,
} from "./hooks";

function Galat({ pesan }: { pesan: string }) {
  return (
    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
      {pesan}
    </p>
  );
}

function KebutuhanForm({ fase }: { fase: Fase }) {
  const { tampilkan } = useToast();
  const nutrisi = useDaftarNutrisi();
  const kebutuhan = useKebutuhanFase(fase.id);
  const simpan = useSimpanKebutuhan(fase.id);
  const [nilai, setNilai] = useState<Record<string, { min?: string; maks?: string }>>({});
  const [galat, setGalat] = useState<string | null>(null);

  const ambilNilai = (id: string, sisi: "min" | "maks") => {
    const lokal = nilai[id]?.[sisi];
    if (lokal !== undefined) return lokal;
    const ada = kebutuhan.data?.find((k) => k.nutrisi_id === id);
    const v = sisi === "min" ? ada?.batas_min : ada?.batas_max;
    return v == null ? "" : String(v);
  };

  const kirim = () => {
    const baris: { nutrisi_id: string; batas_min: number | null; batas_max: number | null }[] = [];
    for (const n of nutrisi.data ?? []) {
      const mn = keAngka(ambilNilai(n.id, "min"));
      const mx = keAngka(ambilNilai(n.id, "maks"));
      if (mn === undefined || mx === undefined) return setGalat(`Batas ${n.nama} harus berupa angka.`);
      if (mn !== null && mx !== null && mn > mx) return setGalat(`Batas minimum ${n.nama} tidak boleh melebihi maksimum.`);
      if (mn !== null || mx !== null) baris.push({ nutrisi_id: n.id, batas_min: mn, batas_max: mx });
    }
    setGalat(null);
    simpan.mutate(baris, { onSuccess: () => tampilkan("Kebutuhan nutrisi disimpan", { tipe: "sukses" }) });
  };

  if (nutrisi.isPending || kebutuhan.isPending) return <Spinner label="Memuat kebutuhan..." />;
  if (nutrisi.isError || kebutuhan.isError) return <ErrorState pesan={pesanGalat(nutrisi.error ?? kebutuhan.error)} />;
  if (nutrisi.data.length === 0) return <p className="text-sm text-stone-500">Tambahkan nutrisi terlebih dahulu.</p>;

  return (
    <div className="space-y-3">
      <ul className="space-y-2">
        {nutrisi.data.map((n) => (
          <li key={n.id} className="grid grid-cols-[1fr_5.5rem_5.5rem] items-center gap-2">
            <span className="text-sm text-stone-800">
              {n.nama} <span className="text-stone-500">({n.satuan})</span>
            </span>
            {(["min", "maks"] as const).map((sisi) => (
              <input
                key={sisi}
                aria-label={`${n.nama} ${sisi === "min" ? "minimum" : "maksimum"}`}
                inputMode="decimal"
                placeholder={sisi === "min" ? "min" : "maks"}
                value={ambilNilai(n.id, sisi)}
                onChange={(e) => setNilai((s) => ({ ...s, [n.id]: { ...s[n.id], [sisi]: e.target.value } }))}
                className="min-h-10 rounded-lg border border-stone-300 px-2 text-right text-sm"
              />
            ))}
          </li>
        ))}
      </ul>
      {galat && <Galat pesan={galat} />}
      {simpan.isError && <Galat pesan={pesanGalat(simpan.error)} />}
      <Button memuat={simpan.isPending} onClick={kirim}>
        Simpan kebutuhan
      </Button>
    </div>
  );
}

function StandarForm({ fase }: { fase: Fase }) {
  const { tampilkan } = useToast();
  const standar = useStandarFase(fase.id);
  const simpan = useSimpanStandar(fase.id);
  const [nilai, setNilai] = useState<Record<string, string>>({});
  const [galat, setGalat] = useState<string | null>(null);

  const KOLOM = [
    { k: "gram_per_ekor_per_hari", label: "Gram per ekor per hari" },
    { k: "frekuensi_makan", label: "Frekuensi makan per hari" },
    { k: "durasi_aduk", label: "Durasi aduk (detik)" },
    { k: "volume_air", label: "Volume air (liter)" },
  ] as const;

  const ambilNilai = (k: (typeof KOLOM)[number]["k"]) => nilai[k] ?? (standar.data ? String(standar.data[k]) : "");

  const kirim = () => {
    const hasil: Record<string, number> = {};
    for (const { k, label } of KOLOM) {
      const n = keAngka(ambilNilai(k));
      if (n == null || n <= 0) return setGalat(`${label} harus berupa angka lebih dari nol.`);
      hasil[k] = n;
    }
    if (!Number.isInteger(hasil.frekuensi_makan) || !Number.isInteger(hasil.durasi_aduk)) {
      return setGalat("Frekuensi makan dan durasi aduk harus bilangan bulat.");
    }
    setGalat(null);
    simpan.mutate(hasil as never, { onSuccess: () => tampilkan("Standar konsumsi disimpan", { tipe: "sukses" }) });
  };

  if (standar.isPending) return <Spinner label="Memuat standar..." />;
  if (standar.isError) return <ErrorState pesan={pesanGalat(standar.error)} />;
  return (
    <div className="space-y-3">
      {standar.data === null && <p className="text-sm text-stone-500">Standar konsumsi belum diisi.</p>}
      {KOLOM.map(({ k, label }) => (
        <Field key={k} label={label} inputMode="decimal" value={ambilNilai(k)} onChange={(e) => setNilai((s) => ({ ...s, [k]: e.target.value }))} />
      ))}
      {galat && <Galat pesan={galat} />}
      {simpan.isError && <Galat pesan={pesanGalat(simpan.error)} />}
      <Button memuat={simpan.isPending} onClick={kirim}>
        Simpan standar
      </Button>
    </div>
  );
}

export default function JenisAyamDetailPage() {
  const { id = "" } = useParams();
  const { tampilkan } = useToast();
  const jenis = useJenisAyam(id);
  const fase = useDaftarFase(id);
  const simpan = useSimpanFase(id);
  const hapus = useHapusFase();
  const [form, setForm] = useState<Fase | "baru" | null>(null);
  const [nama, setNama] = useState("");
  const [umurMin, setUmurMin] = useState("");
  const [umurMaks, setUmurMaks] = useState("");
  const [galatLokal, setGalatLokal] = useState<string | null>(null);
  const [akanHapus, setAkanHapus] = useState<Fase | null>(null);
  const [atur, setAtur] = useState<Fase | null>(null);

  const bukaForm = (f: Fase | "baru") => {
    setNama(f === "baru" ? "" : f.nama);
    setUmurMin(f === "baru" ? "" : String(f.umur_min_hari));
    setUmurMaks(f === "baru" ? "" : String(f.umur_max_hari));
    setGalatLokal(null);
    simpan.reset();
    setForm(f);
  };

  const kirim = () => {
    const mn = keAngka(umurMin);
    const mx = keAngka(umurMaks);
    if (mn == null || mx == null || !Number.isInteger(mn) || !Number.isInteger(mx) || mn < 0) {
      return setGalatLokal("Umur harus berupa bilangan bulat nol atau lebih.");
    }
    if (mn > mx) return setGalatLokal("Umur awal tidak boleh melebihi umur akhir.");
    setGalatLokal(null);
    simpan.mutate(
      { id: form && form !== "baru" ? form.id : undefined, data: { nama: nama.trim(), umur_min_hari: mn, umur_max_hari: mx } },
      {
        onSuccess: () => {
          setForm(null);
          tampilkan("Fase disimpan", { tipe: "sukses" });
        },
      },
    );
  };

  const kembali = (
    <Link to="/master-data" className="inline-flex min-h-11 items-center gap-1 text-sm text-brand-700 hover:underline">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Master data
    </Link>
  );

  if (jenis.isPending) return <Spinner label="Memuat jenis ayam..." />;
  if (jenis.isError) {
    const tidakAda = jenis.error instanceof ApiError && (jenis.error.status === 404 || jenis.error.status === 422);
    return (
      <div className="space-y-3">
        {kembali}
        {tidakAda ? (
          <EmptyState judul="Jenis ayam tidak ditemukan" />
        ) : (
          <ErrorState pesan={pesanGalat(jenis.error)} ulangi={() => void jenis.refetch()} />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {kembali}
      <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">{jenis.data.nama}</h1>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-stone-900">Fase</h2>
        <Button onClick={() => bukaForm("baru")}>Tambah fase</Button>
      </div>
      {fase.isPending && <Spinner label="Memuat fase..." />}
      {fase.isError && <ErrorState pesan={pesanGalat(fase.error)} ulangi={() => void fase.refetch()} />}
      {fase.data && fase.data.length === 0 && <EmptyState judul="Belum ada fase" />}
      {fase.data && fase.data.length > 0 && (
        <ul className="space-y-2">
          {[...fase.data]
            .sort((a, b) => a.umur_min_hari - b.umur_min_hari)
            .map((f) => (
              <li key={f.id}>
                <Card className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-stone-900">{f.nama}</p>
                    <p className="text-sm text-stone-500">
                      Umur {f.umur_min_hari}–{f.umur_max_hari} hari
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button varian="sekunder" onClick={() => setAtur(f)} aria-label={`Atur nutrisi ${f.nama}`}>
                      Nutrisi dan konsumsi
                    </Button>
                    <Button varian="sekunder" onClick={() => bukaForm(f)} aria-label={`Ubah ${f.nama}`}>
                      Ubah
                    </Button>
                    <Button varian="ghost" onClick={() => { hapus.reset(); setAkanHapus(f); }} aria-label={`Hapus ${f.nama}`}>
                      Hapus
                    </Button>
                  </div>
                </Card>
              </li>
            ))}
        </ul>
      )}

      <FormDialog
        judul={form === "baru" ? "Tambah fase" : "Ubah fase"}
        buka={form !== null}
        saatTutup={() => setForm(null)}
        memuat={simpan.isPending}
        galat={galatLokal ?? simpan.error}
        saatKirim={kirim}
      >
        <Field label="Nama" value={nama} onChange={(e) => setNama(e.target.value)} required />
        <Field label="Umur awal (hari)" inputMode="numeric" value={umurMin} onChange={(e) => setUmurMin(e.target.value)} required />
        <Field label="Umur akhir (hari)" inputMode="numeric" value={umurMaks} onChange={(e) => setUmurMaks(e.target.value)} required />
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
              tampilkan("Fase dihapus", { tipe: "sukses" });
            },
          })
        }
      />

      {atur && (
        <Dialog buka saatBerubah={(b) => !b && setAtur(null)} judul={`Nutrisi dan konsumsi: ${atur.nama}`}>
          <div className="max-h-[70vh] space-y-6 overflow-y-auto pr-1">
            <section className="space-y-2">
              <h3 className="font-semibold text-stone-900">Kebutuhan nutrisi</h3>
              <KebutuhanForm fase={atur} />
            </section>
            <section className="space-y-2">
              <h3 className="font-semibold text-stone-900">Standar konsumsi</h3>
              <StandarForm fase={atur} />
            </section>
          </div>
        </Dialog>
      )}
    </div>
  );
}

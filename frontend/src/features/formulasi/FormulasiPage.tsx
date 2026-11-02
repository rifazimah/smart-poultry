import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { pesanGalat } from "../../api/errors";
import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { formatRupiah, formatWaktu } from "../../lib/format";
import { useSiklusAktif } from "../kandang/useDetailKandang";
import { HasilFormulasi } from "./HasilFormulasi";
import {
  useBahanPakan,
  useDetailFormulasi,
  useHitungManual,
  useHitungOtomatis,
  useRiwayatFormulasi,
  useSimpanFormulasi,
  type Preview,
} from "./useFormulasi";

const NADA: Record<string, NadaBadge> = { VALID: "baik", TIDAK_SEMPURNA: "peringatan", PERLU_DITINJAU: "peringatan" };
const LABEL: Record<string, string> = { VALID: "Valid", TIDAK_SEMPURNA: "Tidak sempurna", PERLU_DITINJAU: "Perlu ditinjau" };

function Memuat({ label }: { label: string }) {
  return (
    <div className="py-6 text-center">
      <Spinner label={label} />
    </div>
  );
}

function FormManual({ onHitung, memuat }: { onHitung: (item: { bahan_pakan_id: string; proporsi: number }[]) => void; memuat: boolean }) {
  const bahan = useBahanPakan();
  const [persen, setPersen] = useState<Record<string, string>>({});

  if (bahan.isPending) return <Memuat label="Memuat bahan pakan..." />;
  if (bahan.isError) return <ErrorState pesan={pesanGalat(bahan.error)} ulangi={() => void bahan.refetch()} />;
  if (bahan.data.length === 0) return <EmptyState judul="Belum ada bahan pakan" pesan="Tambahkan bahan pakan terlebih dahulu." />;

  const terisi = bahan.data
    .map((b) => ({ id: b.id, nilai: Number(persen[b.id]) }))
    .filter((x) => persen[x.id] !== undefined && persen[x.id] !== "" && Number.isFinite(x.nilai) && x.nilai > 0);
  const total = terisi.reduce((a, x) => a + x.nilai, 0);
  const pas = terisi.length > 0 && Math.abs(total - 100) < 0.01;

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
        {bahan.data.map((b) => (
          <li key={b.id} className="flex items-center justify-between gap-3 px-4 py-2">
            <label htmlFor={`p-${b.id}`} className="min-w-0 flex-1 truncate text-sm text-stone-800">
              {b.nama}
            </label>
            <div className="flex items-center gap-1">
              <input
                id={`p-${b.id}`}
                type="number"
                inputMode="decimal"
                min={0}
                max={100}
                step="any"
                value={persen[b.id] ?? ""}
                onChange={(e) => setPersen((s) => ({ ...s, [b.id]: e.target.value }))}
                className="min-h-10 w-24 rounded-lg border border-stone-300 px-2 text-right text-sm"
              />
              <span className="text-sm text-stone-500">%</span>
            </div>
          </li>
        ))}
      </ul>
      <p className={`text-sm ${pas ? "text-brand-700" : "text-stone-500"}`}>Total: {Math.round(total * 100) / 100}% (harus 100%)</p>
      <Button
        disabled={!pas}
        memuat={memuat}
        onClick={() => onHitung(terisi.map((x) => ({ bahan_pakan_id: x.id, proporsi: x.nilai / 100 })))}
      >
        Hitung formulasi manual
      </Button>
    </div>
  );
}

function BagianBuat({ siklusId }: { siklusId: string }) {
  const [mode, setMode] = useState<"OTOMATIS" | "MANUAL">("OTOMATIS");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [tersimpan, setTersimpan] = useState(false);
  const otomatis = useHitungOtomatis(siklusId);
  const manual = useHitungManual(siklusId);
  const simpan = useSimpanFormulasi(siklusId);

  const tampilkan = (p: Preview) => {
    setPreview(p);
    setTersimpan(false);
    simpan.reset();
  };
  const galatHitung = otomatis.error ?? manual.error;

  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-stone-900">Buat formulasi baru</h2>
      <div role="radiogroup" aria-label="Mode formulasi" className="flex gap-2">
        {(["OTOMATIS", "MANUAL"] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={mode === m}
            onClick={() => setMode(m)}
            className={`min-h-10 rounded-lg border px-4 text-sm font-medium ${
              mode === m ? "border-brand-700 bg-brand-100 text-brand-800" : "border-stone-300 bg-white text-stone-700"
            }`}
          >
            {m === "OTOMATIS" ? "Otomatis" : "Manual"}
          </button>
        ))}
      </div>

      {mode === "OTOMATIS" ? (
        <div className="space-y-2">
          <p className="text-sm text-stone-500">Sistem mencari komposisi berbiaya terendah yang memenuhi kebutuhan nutrisi fase ini.</p>
          <Button memuat={otomatis.isPending} onClick={() => otomatis.mutate(undefined, { onSuccess: tampilkan })}>
            Hitung otomatis
          </Button>
        </div>
      ) : (
        <FormManual memuat={manual.isPending} onHitung={(item) => manual.mutate(item, { onSuccess: tampilkan })} />
      )}

      {galatHitung && <ErrorState pesan={pesanGalat(galatHitung)} />}

      {preview && (
        <Card className="space-y-4">
          <h3 className="font-semibold text-stone-900">Pratinjau (belum disimpan)</h3>
          <HasilFormulasi data={preview} />
          {simpan.isError && <ErrorState pesan={pesanGalat(simpan.error)} />}
          {tersimpan ? (
            <p role="status" className="text-sm font-medium text-brand-700">
              Formulasi tersimpan.
            </p>
          ) : (
            <Button
              memuat={simpan.isPending}
              onClick={() =>
                simpan.mutate(preview, {
                  onSuccess: () => {
                    setTersimpan(true);
                    setPreview(null);
                  },
                })
              }
            >
              Simpan formulasi
            </Button>
          )}
        </Card>
      )}
      {tersimpan && !preview && (
        <p role="status" className="text-sm font-medium text-brand-700">
          Formulasi tersimpan.
        </p>
      )}
    </section>
  );
}

function BagianRiwayat({ siklusId }: { siklusId: string }) {
  const riwayat = useRiwayatFormulasi(siklusId);
  const [pilihan, setPilihan] = useState<string | null>(null);
  const detail = useDetailFormulasi(pilihan);

  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-stone-900">Riwayat formulasi</h2>
      {riwayat.isPending && <Memuat label="Memuat riwayat..." />}
      {riwayat.isError && <ErrorState pesan={pesanGalat(riwayat.error)} ulangi={() => void riwayat.refetch()} />}
      {riwayat.data && riwayat.data.length === 0 && <EmptyState judul="Belum ada formulasi tersimpan" />}
      {riwayat.data && riwayat.data.length > 0 && (
        <ul className="space-y-2">
          {riwayat.data.map((f) => (
            <li key={f.id}>
              <Card className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <Badge nada={NADA[f.status]}>{LABEL[f.status]}</Badge>
                  <Badge>{f.mode === "OTOMATIS" ? "Otomatis" : "Manual"}</Badge>
                  {f.aktif && <Badge nada="baik">Aktif</Badge>}
                  <span className="text-stone-500">
                    {formatWaktu(f.dibuat_pada)} · {formatRupiah(f.total_biaya_per_kg)}/kg
                  </span>
                </div>
                <Button varian="sekunder" onClick={() => setPilihan(pilihan === f.id ? null : f.id)}>
                  {pilihan === f.id ? "Tutup" : "Lihat"}
                </Button>
              </Card>
              {pilihan === f.id && (
                <div className="mt-2 rounded-xl border border-stone-200 bg-white p-4">
                  {detail.isPending && <Memuat label="Memuat formulasi..." />}
                  {detail.isError && <ErrorState pesan={pesanGalat(detail.error)} ulangi={() => void detail.refetch()} />}
                  {detail.data && <HasilFormulasi data={detail.data} />}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function FormulasiPage() {
  const { id = "" } = useParams();
  const siklus = useSiklusAktif(id);

  const kembali = (
    <Link to={`/kandang/${id}`} className="inline-flex min-h-11 items-center gap-1 text-sm text-brand-700 hover:underline">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Kembali ke kandang
    </Link>
  );

  return (
    <div className="space-y-5">
      {kembali}
      <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Formulasi pakan</h1>
      {siklus.isPending && <Memuat label="Memuat siklus..." />}
      {siklus.isError && <ErrorState pesan={pesanGalat(siklus.error)} ulangi={() => void siklus.refetch()} />}
      {siklus.data === null && (
        <EmptyState judul="Kandang kosong" pesan="Formulasi dibuat untuk siklus yang sedang berjalan. Mulai siklus terlebih dahulu." />
      )}
      {siklus.data && (
        <>
          <BagianBuat siklusId={siklus.data.id} />
          <BagianRiwayat siklusId={siklus.data.id} />
        </>
      )}
    </div>
  );
}

import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, pesanGalat } from "../../api/errors";
import { useAuth } from "../../auth/auth-context";
import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { formatAngka, formatTanggal, formatWaktu } from "../../lib/format";
import {
  useAlatKandang,
  useKandang,
  useNamaJenisFase,
  usePopulasi,
  useSiklusAktif,
  useStokKandang,
  type Stok,
} from "./useDetailKandang";

const NADA_ALAT: Record<string, NadaBadge> = { ONLINE: "baik", OFFLINE: "netral", ERROR: "bahaya" };
const LABEL_ALAT: Record<string, string> = { ONLINE: "Online", OFFLINE: "Offline", ERROR: "Galat" };
const LABEL_POPULASI: Record<string, string> = { MORTALITAS: "Mortalitas", PANEN: "Panen", PENAMBAHAN: "Penambahan" };

function Bagian({ judul, children }: { judul: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-stone-900">{judul}</h2>
      {children}
    </section>
  );
}

function Memuat({ label }: { label: string }) {
  return (
    <div className="py-6 text-center">
      <Spinner label={label} />
    </div>
  );
}

function menipis(s: Stok): boolean {
  return s.ambang_menipis != null && s.jumlah_estimasi <= s.ambang_menipis;
}

function BagianAlat({ id }: { id: string }) {
  const { data, isPending, isError, error, refetch } = useAlatKandang(id);
  if (isPending) return <Memuat label="Memuat alat..." />;
  if (isError) return <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />;
  if (!data) return <EmptyState judul="Belum ada alat" pesan="Alat pemberi pakan belum didaftarkan untuk kandang ini." />;
  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge nada={NADA_ALAT[data.status] ?? "netral"}>{LABEL_ALAT[data.status] ?? data.status}</Badge>
        <span className="text-sm text-stone-500">Sinkron terakhir: {formatWaktu(data.waktu_terakhir_sinkron)}</span>
      </div>
      <ul className="divide-y divide-stone-100">
        {[...data.wadah]
          .sort((a, b) => a.nomor_wadah - b.nomor_wadah)
          .map((w) => (
            <li key={w.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span className="font-medium text-stone-800">Wadah {w.nomor_wadah}</span>
              <span className="text-stone-500">{w.nama_bahan ?? "Belum diisi bahan"}</span>
            </li>
          ))}
      </ul>
    </Card>
  );
}

function BagianStok({ id }: { id: string }) {
  const { data, isPending, isError, error, refetch } = useStokKandang(id);
  if (isPending) return <Memuat label="Memuat stok..." />;
  if (isError) return <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />;
  if (data.length === 0) return <EmptyState judul="Belum ada stok" pesan="Stok muncul setelah wadah alat terdaftar." />;
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {data.map((s) => (
        <li key={s.id}>
          <Card className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium text-stone-800">{s.nama_bahan ?? "Wadah tanpa bahan"}</p>
              <p className="text-sm text-stone-500">{formatAngka(s.jumlah_estimasi, "kg")}</p>
            </div>
            {menipis(s) && <Badge nada="peringatan">Menipis</Badge>}
          </Card>
        </li>
      ))}
    </ul>
  );
}

function BagianSiklus({ id }: { id: string }) {
  const { pengguna } = useAuth();
  const siklus = useSiklusAktif(id);
  const { jenis, fase } = useNamaJenisFase(siklus.data);
  const populasi = usePopulasi(siklus.data?.id);

  if (siklus.isPending) return <Memuat label="Memuat siklus..." />;
  if (siklus.isError) return <ErrorState pesan={pesanGalat(siklus.error)} ulangi={() => void siklus.refetch()} />;
  if (!siklus.data) return <EmptyState judul="Kandang kosong" pesan="Belum ada siklus pemeliharaan yang aktif." />;

  return (
    <div className="space-y-3">
      {pengguna?.role === "PEMILIK" && (
        <Link
          to={`/kandang/${id}/formulasi`}
          className="inline-flex min-h-10 items-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800"
        >
          Kelola formulasi pakan
        </Link>
      )}
      <Card className="grid gap-3 text-sm sm:grid-cols-4">
        <Fakta label="Jenis ayam" nilai={jenis?.nama ?? "..."} />
        <Fakta label="Fase" nilai={fase?.nama ?? "..."} />
        <Fakta label="Jumlah ayam" nilai={formatAngka(siklus.data.jumlah_ayam)} />
        <Fakta label="Mulai" nilai={formatTanggal(siklus.data.tanggal_mulai)} />
      </Card>
      <h3 className="text-sm font-semibold text-stone-700">Riwayat populasi</h3>
      {populasi.isPending && <Memuat label="Memuat populasi..." />}
      {populasi.isError && <ErrorState pesan={pesanGalat(populasi.error)} ulangi={() => void populasi.refetch()} />}
      {populasi.data && populasi.data.length === 0 && (
        <p className="text-sm text-stone-500">Belum ada perubahan populasi.</p>
      )}
      {populasi.data && populasi.data.length > 0 && (
        <Card className="p-0">
          <ul className="divide-y divide-stone-100">
            {populasi.data.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                <span>
                  <span className="font-medium text-stone-800">{LABEL_POPULASI[p.jenis] ?? p.jenis}</span>
                  {p.catatan && <span className="text-stone-500"> · {p.catatan}</span>}
                </span>
                <span className="shrink-0 text-stone-500">
                  {formatAngka(p.jumlah)} ekor · {formatTanggal(p.tanggal)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Fakta({ label, nilai }: { label: string; nilai: string }) {
  return (
    <div>
      <p className="text-xs text-stone-500">{label}</p>
      <p className="font-medium text-stone-900">{nilai}</p>
    </div>
  );
}

export default function KandangDetailPage() {
  const { id = "" } = useParams();
  const kandang = useKandang(id);

  const tautanKembali = (
    <Link to="/" className="inline-flex min-h-11 items-center gap-1 text-sm text-brand-700 hover:underline">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Semua kandang
    </Link>
  );

  if (kandang.isPending) return <Memuat label="Memuat kandang..." />;
  if (kandang.isError) {
    const tidakAda = kandang.error instanceof ApiError && (kandang.error.status === 404 || kandang.error.status === 422);
    return (
      <div className="space-y-3">
        {tautanKembali}
        {tidakAda ? (
          <EmptyState judul="Kandang tidak ditemukan" pesan="Kandang tidak ada atau Anda tidak memiliki akses." />
        ) : (
          <ErrorState pesan={pesanGalat(kandang.error)} ulangi={() => void kandang.refetch()} />
        )}
      </div>
    );
  }

  const k = kandang.data;
  return (
    <div className="space-y-5">
      {tautanKembali}
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">{k.nama}</h1>
        <Badge nada={k.status === "AKTIF" ? "baik" : "netral"}>{k.status === "AKTIF" ? "Aktif" : "Nonaktif"}</Badge>
      </div>
      <p className="-mt-3 text-sm text-stone-500">{k.lokasi || "Lokasi belum diisi"}</p>
      <Bagian judul="Alat dan wadah">
        <BagianAlat id={id} />
      </Bagian>
      <Bagian judul="Stok pakan">
        <BagianStok id={id} />
      </Bagian>
      <Bagian judul="Siklus pemeliharaan">
        <BagianSiklus id={id} />
      </Bagian>
    </div>
  );
}

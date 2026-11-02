import { ArrowLeft, OctagonAlert } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { pesanGalat } from "../../api/errors";
import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { useToast } from "../../components/ui/toast";
import { formatRupiah, formatWaktu } from "../../lib/format";
import { useRiwayatFormulasi } from "../formulasi/useFormulasi";
import { useAlatKandang, useSiklusAktif } from "../kandang/useDetailKandang";
import { masihJalan, useBeriMakan, useRiwayatPerintah, useStopDarurat, type StatusPerintah } from "./usePerintah";

const LABEL_STATUS: Record<StatusPerintah, string> = {
  PENDING: "Menunggu alat",
  DIAMBIL: "Diambil alat",
  BERJALAN: "Berjalan",
  SUKSES: "Sukses",
  GAGAL: "Gagal",
  TIMEOUT: "Kedaluwarsa",
};
const NADA_STATUS: Record<StatusPerintah, NadaBadge> = {
  PENDING: "netral",
  DIAMBIL: "netral",
  BERJALAN: "peringatan",
  SUKSES: "baik",
  GAGAL: "bahaya",
  TIMEOUT: "bahaya",
};
const LABEL_TIPE: Record<string, string> = {
  BERI_MAKAN: "Beri makan",
  STOP_DARURAT: "Stop darurat",
  TEST: "Uji",
  RESET_ERROR: "Reset galat",
};

function Memuat({ label }: { label: string }) {
  return (
    <div className="py-6 text-center">
      <Spinner label={label} />
    </div>
  );
}

function PanelAksi({ kandangId, siklusId }: { kandangId: string; siklusId: string }) {
  const { tampilkan } = useToast();
  const alat = useAlatKandang(kandangId);
  const formulasi = useRiwayatFormulasi(siklusId);
  const riwayat = useRiwayatPerintah(kandangId);
  const beriMakan = useBeriMakan(kandangId);
  const stop = useStopDarurat(kandangId);
  const [konfirmasiStop, setKonfirmasiStop] = useState(false);

  const aktif = formulasi.data?.find((f) => f.aktif);
  const sedangJalan = riwayat.data?.some((p) => masihJalan(p.status)) ?? false;

  let alasanNonaktif: string | null = null;
  if (alat.data === null) alasanNonaktif = "Kandang ini belum memiliki alat.";
  else if (alat.data?.status === "OFFLINE") alasanNonaktif = "Alat sedang offline.";
  else if (formulasi.isSuccess && !aktif) alasanNonaktif = "Belum ada formulasi aktif untuk siklus ini.";
  else if (sedangJalan) alasanNonaktif = "Alat sedang memproses perintah.";

  return (
    <Card className="space-y-4">
      {formulasi.isError && <ErrorState pesan={pesanGalat(formulasi.error)} ulangi={() => void formulasi.refetch()} />}
      {aktif && (
        <p className="text-sm text-stone-600">
          Formulasi aktif: {aktif.mode === "OTOMATIS" ? "otomatis" : "manual"} · {formatRupiah(aktif.total_biaya_per_kg)}/kg ·{" "}
          {formatWaktu(aktif.dibuat_pada)}
        </p>
      )}
      {beriMakan.isError && <ErrorState pesan={pesanGalat(beriMakan.error)} />}
      {stop.isError && <ErrorState pesan={pesanGalat(stop.error)} />}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          disabled={!aktif || alasanNonaktif !== null}
          memuat={beriMakan.isPending}
          onClick={() =>
            aktif &&
            beriMakan.mutate(aktif.id, { onSuccess: () => tampilkan("Perintah beri makan dikirim", { tipe: "sukses" }) })
          }
        >
          Beri makan sekarang
        </Button>
        <Button varian="bahaya" onClick={() => setKonfirmasiStop(true)} disabled={alat.data === null}>
          <OctagonAlert className="h-4 w-4" aria-hidden="true" /> Stop darurat
        </Button>
      </div>
      {alasanNonaktif && <p className="text-sm text-stone-500">{alasanNonaktif}</p>}

      <Dialog
        buka={konfirmasiStop}
        saatBerubah={setKonfirmasiStop}
        judul="Hentikan pemberian pakan?"
        deskripsi="Perintah yang sedang berjalan dibatalkan dan alat diminta berhenti segera."
      >
        <div className="flex justify-end gap-2">
          <Button varian="sekunder" onClick={() => setKonfirmasiStop(false)}>
            Batal
          </Button>
          <Button
            varian="bahaya"
            memuat={stop.isPending}
            onClick={() =>
              stop.mutate(undefined, {
                onSuccess: () => {
                  setKonfirmasiStop(false);
                  tampilkan("Stop darurat dikirim", { tipe: "sukses" });
                },
                onError: () => setKonfirmasiStop(false),
              })
            }
          >
            Ya, hentikan
          </Button>
        </div>
      </Dialog>
    </Card>
  );
}

function Riwayat({ kandangId }: { kandangId: string }) {
  const { data, isPending, isError, error, refetch } = useRiwayatPerintah(kandangId);
  if (isPending) return <Memuat label="Memuat riwayat..." />;
  if (isError) return <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />;
  if (data.length === 0) return <EmptyState judul="Belum ada perintah" />;
  return (
    <Card className="p-0">
      <ul className="divide-y divide-stone-100">
        {data.map((p) => (
          <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
            <span className="font-medium text-stone-800">{LABEL_TIPE[p.tipe] ?? p.tipe}</span>
            <span className="flex items-center gap-3">
              <span className="text-stone-500">{formatWaktu(p.dibuat_pada)}</span>
              <Badge nada={NADA_STATUS[p.status]}>{LABEL_STATUS[p.status]}</Badge>
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export default function BeriMakanPage() {
  const { id = "" } = useParams();
  const siklus = useSiklusAktif(id);

  return (
    <div className="space-y-5">
      <Link to={`/kandang/${id}`} className="inline-flex min-h-11 items-center gap-1 text-sm text-brand-700 hover:underline">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Kembali ke kandang
      </Link>
      <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Beri makan</h1>
      {siklus.isPending && <Memuat label="Memuat siklus..." />}
      {siklus.isError && <ErrorState pesan={pesanGalat(siklus.error)} ulangi={() => void siklus.refetch()} />}
      {siklus.data === null && (
        <EmptyState judul="Kandang kosong" pesan="Pemberian pakan butuh siklus yang sedang berjalan." />
      )}
      {siklus.data && (
        <>
          <PanelAksi kandangId={id} siklusId={siklus.data.id} />
          <section className="space-y-2">
            <h2 className="text-base font-semibold text-stone-900">Riwayat perintah</h2>
            <Riwayat kandangId={id} />
          </section>
        </>
      )}
    </div>
  );
}

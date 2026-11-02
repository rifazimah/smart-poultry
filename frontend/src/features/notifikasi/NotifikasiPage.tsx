import { pesanGalat } from "../../api/errors";
import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { formatWaktu } from "../../lib/format";
import { useDaftarNotifikasi, useTandaiBaca, useTandaiSemuaBaca, type Notifikasi } from "./useDaftarNotifikasi";

const LABEL: Record<Notifikasi["jenis"], string> = {
  PERINTAH_SUKSES: "Perintah sukses",
  PERINTAH_GAGAL: "Perintah gagal",
  ALAT_OFFLINE: "Alat offline",
  ALAT_ERROR: "Alat galat",
  STOK_MENIPIS: "Stok menipis",
  STOK_KOSONG: "Stok kosong",
  PERLU_DITINJAU: "Perlu ditinjau",
};
const NADA: Record<Notifikasi["jenis"], NadaBadge> = {
  PERINTAH_SUKSES: "baik",
  PERINTAH_GAGAL: "bahaya",
  ALAT_OFFLINE: "peringatan",
  ALAT_ERROR: "bahaya",
  STOK_MENIPIS: "peringatan",
  STOK_KOSONG: "bahaya",
  PERLU_DITINJAU: "peringatan",
};

export default function NotifikasiPage() {
  const { data, isPending, isError, error, refetch } = useDaftarNotifikasi();
  const tandai = useTandaiBaca();
  const semua = useTandaiSemuaBaca();
  const adaBelumDibaca = data?.items.some((n) => n.status === "BELUM_DIBACA") ?? false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Notifikasi</h1>
        <Button varian="sekunder" disabled={!adaBelumDibaca} memuat={semua.isPending} onClick={() => semua.mutate()}>
          Tandai semua dibaca
        </Button>
      </div>
      {(tandai.isError || semua.isError) && <ErrorState pesan={pesanGalat(tandai.error ?? semua.error)} />}
      {isPending && (
        <div className="py-10 text-center">
          <Spinner label="Memuat notifikasi..." />
        </div>
      )}
      {isError && <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />}
      {data && data.items.length === 0 && <EmptyState judul="Belum ada notifikasi" />}
      {data && data.items.length > 0 && (
        <ul className="space-y-2">
          {data.items.map((n) => {
            const baru = n.status === "BELUM_DIBACA";
            return (
              <li key={n.id}>
                <Card className={`space-y-1 ${baru ? "border-brand-300 bg-brand-50" : ""}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge nada={NADA[n.jenis]}>{LABEL[n.jenis]}</Badge>
                    <span className="text-xs text-stone-500">{formatWaktu(n.dibuat_pada)}</span>
                  </div>
                  <p className="font-medium text-stone-900">{n.judul}</p>
                  <p className="text-sm text-stone-600">{n.pesan}</p>
                  {baru && (
                    <Button varian="ghost" className="-ml-3" onClick={() => tandai.mutate(n.id)}>
                      Tandai dibaca
                    </Button>
                  )}
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

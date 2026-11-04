import { useState } from "react";
import { pesanGalat } from "../../api/errors";
import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { useToast } from "../../components/ui/toast";
import { formatTanggal, hariIni } from "../../lib/format";
import { useDaftarKandang } from "../dashboard/useKandang";
import {
  useAkhiriPenugasan,
  useBuatPekerja,
  useDaftarPekerja,
  usePenugasanAktif,
  useTugaskan,
  useUbahStatusPekerja,
  type Pekerja,
} from "./hooks";

const LABEL_STATUS: Record<Pekerja["status"], string> = {
  AKTIF: "Aktif",
  NONAKTIF: "Nonaktif",
  WAJIB_GANTI_SANDI: "Wajib ganti sandi",
};
const NADA_STATUS: Record<Pekerja["status"], NadaBadge> = { AKTIF: "baik", NONAKTIF: "netral", WAJIB_GANTI_SANDI: "peringatan" };

function Galat({ pesan }: { pesan: string }) {
  return (
    <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
      {pesan}
    </p>
  );
}

function FormPekerjaBaru({ saatTutup }: { saatTutup: () => void }) {
  const { tampilkan } = useToast();
  const buat = useBuatPekerja();
  const [nama, setNama] = useState("");
  const [email, setEmail] = useState("");
  const [sandi, setSandi] = useState("");
  const [galat, setGalat] = useState<string | null>(null);

  const kirim = () => {
    if (sandi.length < 8) return setGalat("Kata sandi awal minimal 8 karakter.");
    setGalat(null);
    buat.mutate(
      { nama: nama.trim(), email: email.trim(), kata_sandi: sandi, role: "PEKERJA" },
      {
        onSuccess: () => {
          tampilkan("Pekerja ditambahkan", { tipe: "sukses" });
          saatTutup();
        },
      },
    );
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        kirim();
      }}
    >
      <Field label="Nama" value={nama} onChange={(e) => setNama(e.target.value)} required />
      <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <Field
        label="Kata sandi awal"
        type="password"
        autoComplete="new-password"
        value={sandi}
        onChange={(e) => setSandi(e.target.value)}
        required
        bantuan="Sampaikan kepada pekerja secara langsung."
      />
      {galat && <Galat pesan={galat} />}
      {buat.isError && <Galat pesan={pesanGalat(buat.error)} />}
      <div className="flex justify-end gap-2">
        <Button varian="sekunder" onClick={saatTutup}>
          Batal
        </Button>
        <Button type="submit" memuat={buat.isPending}>
          Simpan
        </Button>
      </div>
    </form>
  );
}

function PanelPenugasan({ pekerja }: { pekerja: Pekerja }) {
  const { tampilkan } = useToast();
  const daftar = usePenugasanAktif(pekerja.id);
  const kandang = useDaftarKandang(0, 100);
  const tugaskan = useTugaskan(pekerja.id);
  const akhiri = useAkhiriPenugasan(pekerja.id);
  const [kandangId, setKandangId] = useState("");
  const [tanggal, setTanggal] = useState(hariIni());

  const sudahDitugaskan = new Set(daftar.data?.map((p) => p.kandang_id));
  const pilihan = kandang.data?.items.filter((k) => !sudahDitugaskan.has(k.id)) ?? [];

  return (
    <div className="space-y-4">
      {daftar.isPending && <Spinner label="Memuat penugasan..." />}
      {daftar.isError && <ErrorState pesan={pesanGalat(daftar.error)} ulangi={() => void daftar.refetch()} />}
      {daftar.data && daftar.data.length === 0 && <p className="text-sm text-stone-500">Belum ditugaskan ke kandang mana pun.</p>}
      {daftar.data && daftar.data.length > 0 && (
        <ul className="divide-y divide-stone-100 rounded-xl border border-stone-200">
          {daftar.data.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
              <span>
                <span className="font-medium text-stone-800">{p.nama_kandang}</span>
                <span className="text-stone-500"> · sejak {formatTanggal(p.tanggal_mulai)}</span>
              </span>
              <Button
                varian="ghost"
                aria-label={`Akhiri penugasan ${p.nama_kandang}`}
                memuat={akhiri.isPending && akhiri.variables === p.id}
                onClick={() =>
                  akhiri.mutate(p.id, { onSuccess: () => tampilkan("Penugasan diakhiri", { tipe: "sukses" }) })
                }
              >
                Akhiri
              </Button>
            </li>
          ))}
        </ul>
      )}
      {akhiri.isError && <Galat pesan={pesanGalat(akhiri.error)} />}

      <form
        className="space-y-3 border-t border-stone-200 pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          tugaskan.mutate(
            { kandang_id: kandangId, tanggal_mulai: tanggal },
            {
              onSuccess: () => {
                setKandangId("");
                tampilkan("Pekerja ditugaskan", { tipe: "sukses" });
              },
            },
          );
        }}
      >
        <h3 className="font-semibold text-stone-900">Tugaskan ke kandang</h3>
        <div className="space-y-1">
          <label htmlFor="kandang-tugas" className="block text-sm font-medium text-stone-700">
            Kandang
          </label>
          <select
            id="kandang-tugas"
            value={kandangId}
            onChange={(e) => setKandangId(e.target.value)}
            className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm"
          >
            <option value="">Pilih kandang</option>
            {pilihan.map((k) => (
              <option key={k.id} value={k.id}>
                {k.nama}
              </option>
            ))}
          </select>
        </div>
        <Field label="Tanggal mulai" type="date" value={tanggal} onChange={(e) => setTanggal(e.target.value)} required />
        {tugaskan.isError && <Galat pesan={pesanGalat(tugaskan.error)} />}
        <Button type="submit" disabled={!kandangId || !tanggal} memuat={tugaskan.isPending}>
          Tugaskan
        </Button>
      </form>
    </div>
  );
}

export default function PekerjaPage() {
  const { tampilkan } = useToast();
  const daftar = useDaftarPekerja();
  const ubahStatus = useUbahStatusPekerja();
  const [tambah, setTambah] = useState(false);
  const [penugasan, setPenugasan] = useState<Pekerja | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Pekerja</h1>
        <Button onClick={() => setTambah(true)}>Tambah pekerja</Button>
      </div>
      {ubahStatus.isError && <Galat pesan={pesanGalat(ubahStatus.error)} />}
      {daftar.isPending && (
        <div className="py-10 text-center">
          <Spinner label="Memuat pekerja..." />
        </div>
      )}
      {daftar.isError && <ErrorState pesan={pesanGalat(daftar.error)} ulangi={() => void daftar.refetch()} />}
      {daftar.data && daftar.data.length === 0 && (
        <EmptyState judul="Belum ada pekerja" pesan="Tambahkan pekerja lalu tugaskan ke kandang." />
      )}
      {daftar.data && daftar.data.length > 0 && (
        <ul className="space-y-2">
          {daftar.data.map((p) => {
            const aktif = p.status !== "NONAKTIF";
            return (
              <li key={p.id}>
                <Card className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-stone-900">{p.nama}</p>
                    <p className="truncate text-sm text-stone-500">{p.email}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge nada={NADA_STATUS[p.status]}>{LABEL_STATUS[p.status]}</Badge>
                    <Button varian="sekunder" onClick={() => setPenugasan(p)} aria-label={`Penugasan ${p.nama}`}>
                      Penugasan
                    </Button>
                    <Button
                      varian={aktif ? "ghost" : "sekunder"}
                      aria-label={`${aktif ? "Nonaktifkan" : "Aktifkan"} ${p.nama}`}
                      memuat={ubahStatus.isPending && ubahStatus.variables?.id === p.id}
                      onClick={() =>
                        ubahStatus.mutate(
                          { id: p.id, status: aktif ? "NONAKTIF" : "AKTIF" },
                          { onSuccess: () => tampilkan(aktif ? "Pekerja dinonaktifkan" : "Pekerja diaktifkan", { tipe: "sukses" }) },
                        )
                      }
                    >
                      {aktif ? "Nonaktifkan" : "Aktifkan"}
                    </Button>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}

      <Dialog buka={tambah} saatBerubah={setTambah} judul="Tambah pekerja">
        {tambah && <FormPekerjaBaru saatTutup={() => setTambah(false)} />}
      </Dialog>
      {penugasan && (
        <Dialog buka saatBerubah={(b) => !b && setPenugasan(null)} judul={`Penugasan: ${penugasan.nama}`}>
          <PanelPenugasan pekerja={penugasan} />
        </Dialog>
      )}
    </div>
  );
}

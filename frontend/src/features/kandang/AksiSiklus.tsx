import { useState } from "react";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/ui/field";
import { hariIni } from "../../lib/format";
import { FormDialog, KonfirmasiHapus, keAngka, useToast } from "../master-data/bersama";
import { useDaftarFase, useDaftarJenisAyam } from "../master-data/hooks";
import {
  useCatatPopulasi,
  useGantiFase,
  useHapusPopulasi,
  useHapusSiklus,
  useKoreksiSiklus,
  useMulaiSiklus,
  useSelesaiSiklus,
} from "./aksi";
import type { Populasi, Siklus } from "./useDetailKandang";

type Jenis = Populasi["jenis"];

function Pilih({
  id,
  label,
  nilai,
  saatPilih,
  pilihan,
  kosong,
}: {
  id: string;
  label: string;
  nilai: string;
  saatPilih: (v: string) => void;
  pilihan: { id: string; nama: string }[] | undefined;
  kosong: string;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        {label}
      </label>
      <select
        id={id}
        value={nilai}
        required
        onChange={(e) => saatPilih(e.target.value)}
        className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm"
      >
        <option value="">{kosong}</option>
        {pilihan?.map((p) => (
          <option key={p.id} value={p.id}>
            {p.nama}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Mulai siklus pada kandang kosong (Pemilik: butuh daftar jenis ayam dan fase dari master data). */
export function MulaiSiklus({ kandangId }: { kandangId: string }) {
  const { tampilkan } = useToast();
  const mulai = useMulaiSiklus(kandangId);
  const jenis = useDaftarJenisAyam();
  const [buka, setBuka] = useState(false);
  const [jenisId, setJenisId] = useState("");
  const [faseId, setFaseId] = useState("");
  const [jumlah, setJumlah] = useState("");
  const [tanggal, setTanggal] = useState(hariIni());
  const [galatLokal, setGalatLokal] = useState<string | null>(null);
  const fase = useDaftarFase(jenisId);

  const kirim = () => {
    const n = keAngka(jumlah);
    if (!jenisId || !faseId) return setGalatLokal("Pilih jenis ayam dan fase.");
    if (n == null || !Number.isInteger(n) || n < 1) return setGalatLokal("Jumlah ayam harus bilangan bulat 1 atau lebih.");
    setGalatLokal(null);
    mulai.mutate(
      { jenis_ayam_id: jenisId, fase_id: faseId, jumlah_ayam: n, tanggal_mulai: tanggal },
      {
        onSuccess: () => {
          setBuka(false);
          tampilkan("Siklus dimulai", { tipe: "sukses" });
        },
      },
    );
  };

  return (
    <>
      <Button
        onClick={() => {
          setJenisId("");
          setFaseId("");
          setJumlah("");
          setTanggal(hariIni());
          setGalatLokal(null);
          mulai.reset();
          setBuka(true);
        }}
      >
        Mulai siklus
      </Button>
      <FormDialog
        judul="Mulai siklus"
        buka={buka}
        saatTutup={() => setBuka(false)}
        memuat={mulai.isPending}
        galat={galatLokal ?? mulai.error}
        saatKirim={kirim}
      >
        <Pilih
          id="siklus-jenis"
          label="Jenis ayam"
          nilai={jenisId}
          saatPilih={(v) => {
            setJenisId(v);
            setFaseId("");
          }}
          pilihan={jenis.data}
          kosong="Pilih jenis ayam"
        />
        <Pilih
          id="siklus-fase"
          label="Fase"
          nilai={faseId}
          saatPilih={setFaseId}
          pilihan={fase.data && [...fase.data].sort((a, b) => a.umur_min_hari - b.umur_min_hari)}
          kosong={jenisId ? "Pilih fase" : "Pilih jenis ayam dulu"}
        />
        <Field label="Jumlah ayam" inputMode="numeric" value={jumlah} onChange={(e) => setJumlah(e.target.value)} required />
        <Field label="Tanggal mulai" type="date" value={tanggal} onChange={(e) => setTanggal(e.target.value)} required />
      </FormDialog>
    </>
  );
}

const LABEL_JENIS_POPULASI: Record<Jenis, string> = { MORTALITAS: "Mortalitas", PANEN: "Panen", PENAMBAHAN: "Penambahan" };

/** Aksi siklus aktif: catat populasi (semua peran); ganti fase, koreksi, selesai, hapus (Pemilik). */
export function AksiSiklus({ siklus, pemilik }: { siklus: Siklus; pemilik: boolean }) {
  const { tampilkan } = useToast();
  const catat = useCatatPopulasi();
  const ganti = useGantiFase();
  const koreksi = useKoreksiSiklus();
  const selesai = useSelesaiSiklus();
  const hapus = useHapusSiklus();
  const fase = useDaftarFase(siklus.jenis_ayam_id, pemilik);
  const [mode, setMode] = useState<"populasi" | "fase" | "koreksi" | "selesai" | "hapus" | null>(null);
  const [jenis, setJenis] = useState<Jenis>("MORTALITAS");
  const [jumlah, setJumlah] = useState("");
  const [tanggal, setTanggal] = useState(hariIni());
  const [catatan, setCatatan] = useState("");
  const [faseId, setFaseId] = useState("");
  const [galatLokal, setGalatLokal] = useState<string | null>(null);

  const buka = (m: NonNullable<typeof mode>) => {
    setJenis("MORTALITAS");
    setJumlah(m === "koreksi" ? String(siklus.jumlah_ayam) : "");
    setTanggal(m === "koreksi" ? siklus.tanggal_mulai : hariIni());
    setCatatan("");
    setFaseId(siklus.fase_id);
    setGalatLokal(null);
    catat.reset();
    ganti.reset();
    koreksi.reset();
    selesai.reset();
    hapus.reset();
    setMode(m);
  };
  const tutup = () => setMode(null);
  const sukses = (pesan: string) => () => {
    tutup();
    tampilkan(pesan, { tipe: "sukses" });
  };

  const kirimPopulasi = () => {
    const n = keAngka(jumlah);
    if (n == null || !Number.isInteger(n) || n < 1) return setGalatLokal("Jumlah harus bilangan bulat 1 atau lebih.");
    setGalatLokal(null);
    catat.mutate(
      { siklusId: siklus.id, data: { jenis, jumlah: n, tanggal, catatan: catatan.trim() || null } },
      { onSuccess: sukses("Perubahan populasi dicatat") },
    );
  };

  const kirimKoreksi = () => {
    const n = keAngka(jumlah);
    if (n == null || !Number.isInteger(n) || n < 0) return setGalatLokal("Jumlah ayam harus bilangan bulat nol atau lebih.");
    setGalatLokal(null);
    koreksi.mutate({ siklusId: siklus.id, data: { jumlah_ayam: n, tanggal_mulai: tanggal } }, { onSuccess: sukses("Siklus dikoreksi") });
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button varian="sekunder" onClick={() => buka("populasi")}>
        Catat populasi
      </Button>
      {pemilik && (
        <>
          <Button varian="sekunder" onClick={() => buka("fase")}>
            Ganti fase
          </Button>
          <Button varian="sekunder" onClick={() => buka("koreksi")}>
            Koreksi siklus
          </Button>
          <Button varian="sekunder" onClick={() => buka("selesai")}>
            Selesaikan siklus
          </Button>
          <Button varian="ghost" onClick={() => buka("hapus")}>
            Hapus siklus
          </Button>
        </>
      )}

      <FormDialog
        judul="Catat perubahan populasi"
        buka={mode === "populasi"}
        saatTutup={tutup}
        memuat={catat.isPending}
        galat={galatLokal ?? catat.error}
        saatKirim={kirimPopulasi}
      >
        <Pilih
          id="pop-jenis"
          label="Jenis"
          nilai={jenis}
          saatPilih={(v) => setJenis(v as Jenis)}
          pilihan={(Object.keys(LABEL_JENIS_POPULASI) as Jenis[]).map((j) => ({ id: j, nama: LABEL_JENIS_POPULASI[j] }))}
          kosong="Pilih jenis"
        />
        <Field label="Jumlah (ekor)" inputMode="numeric" value={jumlah} onChange={(e) => setJumlah(e.target.value)} required />
        <Field label="Tanggal" type="date" value={tanggal} onChange={(e) => setTanggal(e.target.value)} required />
        <Field label="Catatan (opsional)" value={catatan} onChange={(e) => setCatatan(e.target.value)} />
      </FormDialog>

      <FormDialog
        judul="Ganti fase"
        buka={mode === "fase"}
        saatTutup={tutup}
        memuat={ganti.isPending}
        galat={ganti.error}
        saatKirim={() => ganti.mutate({ siklusId: siklus.id, faseId }, { onSuccess: sukses("Fase diganti") })}
      >
        <Pilih
          id="ganti-fase"
          label="Fase baru"
          nilai={faseId}
          saatPilih={setFaseId}
          pilihan={fase.data && [...fase.data].sort((a, b) => a.umur_min_hari - b.umur_min_hari)}
          kosong="Pilih fase"
        />
        <p className="text-xs text-stone-500">Formulasi yang aktif ditandai perlu ditinjau; hitung ulang formulasi untuk fase baru.</p>
      </FormDialog>

      <FormDialog
        judul="Koreksi siklus"
        buka={mode === "koreksi"}
        saatTutup={tutup}
        memuat={koreksi.isPending}
        galat={galatLokal ?? koreksi.error}
        saatKirim={kirimKoreksi}
      >
        <Field label="Jumlah ayam sekarang" inputMode="numeric" value={jumlah} onChange={(e) => setJumlah(e.target.value)} required />
        <Field label="Tanggal mulai" type="date" value={tanggal} onChange={(e) => setTanggal(e.target.value)} required />
        <p className="text-xs text-stone-500">Gunakan hanya untuk membetulkan salah input; perubahan harian dicatat lewat Catat populasi.</p>
      </FormDialog>

      <KonfirmasiHapus
        nama={mode === "selesai" ? "siklus ini" : null}
        judul="Selesaikan siklus?"
        deskripsi="Siklus ditandai selesai dan tidak bisa dibuka lagi. Kandang menjadi kosong sampai siklus baru dimulai."
        tombol="Selesaikan"
        saatTutup={tutup}
        memuat={selesai.isPending}
        galat={selesai.error}
        saatHapus={() => selesai.mutate(siklus.id, { onSuccess: sukses("Siklus diselesaikan") })}
      />

      <KonfirmasiHapus
        nama={mode === "hapus" ? "siklus ini" : null}
        deskripsi="Siklus beserta catatan populasi dan formulasinya dihapus permanen. Hanya untuk salah input; siklus yang formulasinya sudah dipakai perintah tidak dapat dihapus."
        saatTutup={tutup}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() => hapus.mutate(siklus.id, { onSuccess: sukses("Siklus dihapus") })}
      />
    </div>
  );
}

/** Tombol hapus pada satu baris riwayat populasi (Pemilik). */
export function HapusPopulasi({ siklusId, populasi }: { siklusId: string; populasi: Populasi }) {
  const { tampilkan } = useToast();
  const hapus = useHapusPopulasi();
  const [buka, setBuka] = useState(false);
  return (
    <>
      <Button
        varian="ghost"
        aria-label={`Hapus catatan ${LABEL_JENIS_POPULASI[populasi.jenis]} ${populasi.tanggal}`}
        onClick={() => {
          hapus.reset();
          setBuka(true);
        }}
      >
        Hapus
      </Button>
      <KonfirmasiHapus
        nama={buka ? `${LABEL_JENIS_POPULASI[populasi.jenis]} ${populasi.jumlah} ekor` : null}
        deskripsi="Catatan dihapus dan jumlah ayam dikembalikan seperti sebelum dicatat."
        saatTutup={() => setBuka(false)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          hapus.mutate(
            { siklusId, populasiId: populasi.id },
            {
              onSuccess: () => {
                setBuka(false);
                tampilkan("Catatan populasi dihapus", { tipe: "sukses" });
              },
            },
          )
        }
      />
    </>
  );
}
